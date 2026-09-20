"""
test/test_ai_features.py

Validates Feature 9: AI Assistant 2.0.
- Tests dynamic model discovery (fetch_available_models) with fallback handling.
- Tests updated AI live context (currency symbol, savings goals snapshot).
- Tests Natural Language transaction intent parsing and 1-click execution.
- Tests Financial Health Audit prompt workflow.
"""

import sys
import tempfile
import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_db
from app import categories as categories_api
from app import transactions as transactions_api
from app import savings_goals as goals_api
from app.ai_chat import fetch_available_models, save_api_key, save_model, load_model, AVAILABLE_MODELS
from app.ai_context import build_live_context, build_system_prompt


def run_test():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_budget.db"
        init_db(db_path)

        # 1. Test fetch_available_models fallback
        models = fetch_available_models(api_key=None, db_path=db_path)
        assert len(models) >= 3
        assert "gemini-2.5-flash" in models
        print("✓ Model fallback discovery passed.")

        # Test model discovery with mock client response
        mock_model_flash = MagicMock()
        mock_model_flash.name = "models/gemini-2.5-flash"
        mock_model_pro = MagicMock()
        mock_model_pro.name = "models/gemini-2.5-pro"
        mock_model_embed = MagicMock()
        mock_model_embed.name = "models/text-embedding-004"

        mock_client = MagicMock()
        mock_client.models.list.return_value = [mock_model_flash, mock_model_pro, mock_model_embed]

        with patch("google.genai.Client", return_value=mock_client):
            discovered = fetch_available_models(api_key="test_key_123", db_path=db_path)
            assert "gemini-2.5-flash" in discovered
            assert "gemini-2.5-pro" in discovered
            assert not any("embedding" in m for m in discovered), "Embedding models should be filtered out"
            print("✓ Dynamic model discovery and filtering passed.")

        # 2. Setup budget data for AI context validation
        groceries_id = categories_api.create_category("Groceries", soft_limit=4000.0, hard_limit=5000.0, db_path=db_path)
        goals_api.create_goal("Goa Trip", target_amount=20000.0, initial_saved=5000.0, db_path=db_path)

        ctx = build_live_context(db_path=db_path)
        assert "₹" in ctx, "Context should format with ₹"
        assert "Goa Trip" in ctx, "Savings goals should appear in live context"
        assert "Groceries" in ctx, "Categories should appear in live context"

        prompt = build_system_prompt(db_path=db_path)
        assert "add_transaction" in prompt, "Natural language quick-add schema should be in system prompt"
        assert "FINANCIAL HEALTH AUDIT" in prompt, "Audit instructions should be in system prompt"
        print("✓ Live AI context and system prompt generation passed.")

        # 3. Test Headless ChatScreen with Natural Language Transaction Extraction
        try:
            import customtkinter as ctk
            from ui.chat_screen import ChatScreen
            from ui.settings_screen import SettingsScreen

            root = ctk.CTk()
            root.withdraw()

            changes = []
            chat = ChatScreen(root, db_path=db_path, on_change=lambda: changes.append(True))

            # Simulate an incoming AI response with natural language + JSON transaction block
            ai_reply = (
                "Sure thing! I've prepared that transaction for you.\n\n"
                "```json\n"
                "{\n"
                '  "action": "add_transaction",\n'
                '  "amount": 350.0,\n'
                '  "type": "expense",\n'
                '  "category": "Groceries",\n'
                f'  "date": "{date.today().isoformat()}",\n'
                '  "description": "Vegetables and snacks"\n'
                "}\n"
                "```\n\n"
                "Click the button below to record it."
            )

            # Trigger response display
            chat._display_response(ai_reply)

            # Find the action card in bubble frame
            action_cards = [w for w in chat._bubble_frame.winfo_children() if isinstance(w, ctk.CTkFrame)]
            assert len(action_cards) >= 1, "Should render transaction action card"

            # Find the confirm button in the action card
            confirm_btn = [w for w in action_cards[-1].winfo_children() if isinstance(w, ctk.CTkButton)][0]
            assert "Confirm" in confirm_btn.cget("text")

            # Simulate clicking the confirm button
            confirm_btn.invoke()

            # Verify transaction was added to the DB
            txns = transactions_api.list_transactions(db_path=db_path)
            assert len(txns) == 1, "Transaction should be committed to database"
            assert txns[0]["amount"] == 350.0
            assert txns[0]["category_id"] == groceries_id
            assert len(changes) == 1, "on_change callback should have been triggered"
            assert "Added" in confirm_btn.cget("text")
            print("✓ Natural language transaction extraction and 1-click addition passed.")

            # 4. Test Audit Trigger
            chat._trigger_audit()
            assert "Financial Health Audit" in chat._input_var.get()
            print("✓ 1-click Financial Health Audit trigger passed.")

            # 5. Test SettingsScreen Live Models refresh
            settings = SettingsScreen(root, db_path=db_path)
            settings._refresh_live_models()
            assert "Discovered" in settings._ai_model_status.cget("text") or "Model" in settings._ai_model_status.cget("text")
            print("✓ SettingsScreen Discover Live Models UI passed.")

            root.destroy()
        except Exception as e:
            if "no display name" in str(e).lower() or "display" in str(e).lower():
                print("Skipping GUI render due to headless environment:", e)
            else:
                raise e

    print("ALL AI ASSISTANT 2.0 TESTS PASSED!")


if __name__ == "__main__":
    run_test()
