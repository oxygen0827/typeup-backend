import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path


def _dispose_loaded_engine():
    db_module = sys.modules.get("app.db")
    engine = getattr(db_module, "engine", None)
    if engine is not None:
        engine.dispose()


def _load_app_with_temp_db():
    _dispose_loaded_engine()
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    Path(db_path).unlink(missing_ok=True)

    os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
    os.environ["APP_BASE_URL"] = "http://testserver"
    os.environ["JWT_SECRET"] = "test-secret"
    os.environ["ADMIN_API_KEY"] = "adminkey"
    os.environ["DEV_MOCK_PAYMENTS"] = "true"
    os.environ["DEV_MOCK_MODELS"] = "true"

    import app.config as config
    config.get_settings.cache_clear()

    modules = [
        "app.db",
        "app.models",
        "app.plans",
        "app.services",
        "app.security",
        "app.routers.admin",
        "app.routers.auth",
        "app.routers.billing",
        "app.routers.models",
        "app.routers.payments",
        "app.main",
    ]
    imported = {}
    for name in modules:
        if name in sys.modules:
            imported[name] = importlib.reload(sys.modules[name])
        else:
            imported[name] = importlib.import_module(name)
    return imported["app.main"].app


class ApiFlowTests(unittest.TestCase):
    def tearDown(self):
        _dispose_loaded_engine()

    def test_auth_billing_mock_payment_and_model_flow(self):
        from fastapi.testclient import TestClient

        app = _load_app_with_temp_db()
        with TestClient(app) as client:
            register = client.post("/v1/auth/register", json={
                "email": "demo@example.com",
                "password": "password123",
            })
            self.assertEqual(register.status_code, 200, register.text)
            token = register.json()["access_token"]

            trial_me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(trial_me.status_code, 200, trial_me.text)
            trial = trial_me.json()["entitlement"]
            self.assertTrue(trial["active"])
            self.assertEqual(trial["plan_id"], "free_trial")
            self.assertEqual(trial["stt_minutes_limit"], 600)
            self.assertEqual(trial["ai_requests_limit"], 3000)

            plans = client.get("/v1/plans")
            self.assertEqual(plans.status_code, 200, plans.text)
            self.assertGreaterEqual(len(plans.json()), 1)
            self.assertNotIn("free_trial", {plan["id"] for plan in plans.json()})

            order = client.post(
                "/v1/orders",
                headers={"Authorization": f"Bearer {token}"},
                json={"plan_id": "pro_monthly", "payment_method": "alipay"},
            )
            self.assertEqual(order.status_code, 200, order.text)
            self.assertEqual(order.json()["status"], "pending")
            pay_path = order.json()["pay_url"].removeprefix("http://testserver")

            paid = client.get(pay_path)
            self.assertEqual(paid.status_code, 200, paid.text)

            me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(me.status_code, 200, me.text)
            self.assertTrue(me.json()["entitlement"]["active"])

            llm = client.post(
                "/v1/llm/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"messages": [{"role": "user", "content": "你好"}]},
            )
            self.assertEqual(llm.status_code, 200, llm.text)
            self.assertIn("text", llm.json())

            invalid_llm = client.post(
                "/v1/llm/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"messages": [], "max_tokens": 0, "temperature": 9},
            )
            self.assertEqual(invalid_llm.status_code, 422, invalid_llm.text)
            self.assertEqual(invalid_llm.json()["error"]["code"], "VALIDATION_ERROR")

    def test_refresh_rotation_and_disabled_user_rejection(self):
        from fastapi.testclient import TestClient

        app = _load_app_with_temp_db()
        with TestClient(app) as client:
            register = client.post("/v1/auth/register", json={
                "email": "disabled@example.com",
                "password": "password123",
            })
            self.assertEqual(register.status_code, 200, register.text)
            user_id = register.json()["user"]["id"]
            first_refresh = register.json()["refresh_token"]

            rotated = client.post("/v1/auth/refresh", json={"refresh_token": first_refresh})
            self.assertEqual(rotated.status_code, 200, rotated.text)
            second_refresh = rotated.json()["refresh_token"]

            reused = client.post("/v1/auth/refresh", json={"refresh_token": first_refresh})
            self.assertEqual(reused.status_code, 401, reused.text)

            disabled = client.post(
                f"/admin/users/{user_id}/disable",
                headers={"X-Admin-Key": "adminkey"},
            )
            self.assertEqual(disabled.status_code, 200, disabled.text)

            rejected = client.post("/v1/auth/refresh", json={"refresh_token": second_refresh})
            self.assertEqual(rejected.status_code, 403, rejected.text)
            self.assertEqual(rejected.json()["error"]["code"], "FORBIDDEN")

    def test_register_validation_message_is_actionable(self):
        from fastapi.testclient import TestClient

        app = _load_app_with_temp_db()
        with TestClient(app) as client:
            response = client.post("/v1/auth/register", json={
                "email": "not-an-email",
                "password": "123456",
            })
            self.assertEqual(response.status_code, 422, response.text)
            message = response.json()["error"]["message"]
            self.assertIn("请输入正确的邮箱地址", message)
            self.assertIn("密码至少 8 位", message)

    def test_alipay_notify_rejects_trade_number_conflicts(self):
        _load_app_with_temp_db()
        from app.db import Base, SessionLocal, engine
        from app.models import Order, Payment
        from app.plans import seed_plans
        from app.services import mark_alipay_order_paid

        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_plans(db)
            first = Order(user_id="usr_1", plan_id="pro_monthly", amount_cents=2900)
            second = Order(user_id="usr_1", plan_id="pro_monthly", amount_cents=2900)
            db.add_all([first, second])
            db.flush()

            self.assertTrue(mark_alipay_order_paid(db, {
                "out_trade_no": first.id,
                "trade_no": "trade_shared",
                "trade_status": "TRADE_SUCCESS",
                "total_amount": "29.00",
            }))

            with self.assertRaises(ValueError):
                mark_alipay_order_paid(db, {
                    "out_trade_no": second.id,
                    "trade_no": "trade_shared",
                    "trade_status": "TRADE_SUCCESS",
                    "total_amount": "29.00",
                })

            db.rollback()
            payments = db.query(Payment).filter(Payment.provider_trade_no == "trade_shared").all()
            self.assertEqual(len(payments), 1)

    def test_alipay_notify_rejects_repaying_paid_order_with_new_trade_number(self):
        _load_app_with_temp_db()
        from app.db import Base, SessionLocal, engine
        from app.models import Order
        from app.plans import seed_plans
        from app.services import mark_alipay_order_paid

        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_plans(db)
            order = Order(user_id="usr_1", plan_id="pro_monthly", amount_cents=2900)
            db.add(order)
            db.flush()

            self.assertTrue(mark_alipay_order_paid(db, {
                "out_trade_no": order.id,
                "trade_no": "trade_first",
                "trade_status": "TRADE_SUCCESS",
                "total_amount": "29.00",
            }))

            with self.assertRaises(ValueError):
                mark_alipay_order_paid(db, {
                    "out_trade_no": order.id,
                    "trade_no": "trade_second",
                    "trade_status": "TRADE_SUCCESS",
                    "total_amount": "29.00",
                })


if __name__ == "__main__":
    unittest.main()
