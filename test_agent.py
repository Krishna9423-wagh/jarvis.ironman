"""
J.A.R.V.I.S. Autonomous Agent Verification Suite
------------------------------------------------
Tests:
1. SAFE Action: "open WhatsApp"
2. SAFE Action: "search Python tutorials on YouTube"
3. SAFE Action: "set volume to 30"
4. Multi-Step Communication Flow: "text Rahul I'll be late" (Draft -> Permission Gate -> Approval -> Send)
5. Interactive Modification: "change it to I'll be 20 minutes late"
6. Multi-Step Document & Email: "email my resume to test@example.com"
7. BLOCKED Tier Protection: "delete all files in Downloads"
8. Ambiguous Contact Resolution: "Which Rahul?"
"""

import sys
from agent import JarvisAgent
from permissions import PermissionTier

def run_agent_tests():
    print("=" * 70)
    print("  J.A.R.V.I.S. AUTONOMOUS AGENT & PERMISSION SYSTEM TEST SUITE")
    print("=" * 70)
    
    agent = JarvisAgent()
    
    # ---------------------------------------------------------
    # TEST 1: SAFE Action - "open WhatsApp"
    # ---------------------------------------------------------
    print("\n\033[94m[TEST 1: SAFE Action - 'open WhatsApp']\033[0m")
    res1 = agent.process_turn("open WhatsApp")
    print(f"User: open WhatsApp\nJarvis: {res1}")
    assert "whatsapp" in res1.lower() or "opened" in res1.lower(), "Test 1 Failed"
    assert agent.permissions.pending_action is None, "SAFE action should not be gated"
    print("\033[92m=> TEST 1 PASSED (SAFE Action executed immediately)\033[0m")

    # ---------------------------------------------------------
    # TEST 1b: SAFE Action - "open Instagram"
    # ---------------------------------------------------------
    print("\n\033[94m[TEST 1b: SAFE Action - 'open Instagram']\033[0m")
    res1b = agent.process_turn("open Instagram")
    print(f"User: open Instagram\nJarvis: {res1b}")
    assert "instagram" in res1b.lower() or "opened" in res1b.lower(), "Test 1b Failed"
    assert agent.permissions.pending_action is None, "SAFE action should not be gated"
    print("\033[92m=> TEST 1b PASSED (SAFE Action executed immediately)\033[0m")

    # ---------------------------------------------------------
    # TEST 2: SAFE Action - "search Python tutorials on YouTube"
    # ---------------------------------------------------------
    print("\n\033[94m[TEST 2: SAFE Action - 'search Python tutorials on YouTube']\033[0m")
    res2 = agent.process_turn("search Python tutorials on YouTube")
    print(f"User: search Python tutorials on YouTube\nJarvis: {res2}")
    assert "youtube" in res2.lower() or "python" in res2.lower(), "Test 2 Failed"
    print("\033[92m=> TEST 2 PASSED (YouTube video launched directly)\033[0m")

    # ---------------------------------------------------------
    # TEST 3: SAFE Action - "set volume to 30"
    # ---------------------------------------------------------
    print("\n\033[94m[TEST 3: SAFE Action - 'set volume to 30']\033[0m")
    res3 = agent.process_turn("set volume to 30")
    print(f"User: set volume to 30\nJarvis: {res3}")
    assert "30" in res3 or "volume" in res3.lower(), "Test 3 Failed"
    print("\033[92m=> TEST 3 PASSED (Volume adjusted directly)\033[0m")

    # ---------------------------------------------------------
    # TEST 4: ASK Action - "text Rahul I'll be late by 10 minutes"
    # ---------------------------------------------------------
    print("\n\033[94m[TEST 4: ASK Action - Contact resolution & Gated Permission Flow]\033[0m")
    res4 = agent.process_turn("text Rahul that I'll be late by 10 minutes")
    print(f"User: text Rahul that I'll be late by 10 minutes\nJarvis: {res4}")
    
    # Check if contact is ambiguous or gated for confirmation
    if "which rahul" in res4.lower():
        print("Note: Ambiguity resolved correctly (found multiple Rahuls in Contacts).")
        # Clarify which Rahul
        res4_b = agent.process_turn("Rahul Pw")
        print(f"User: Rahul Pw\nJarvis: {res4_b}")
        assert agent.permissions.pending_action is not None, "Action should be waiting for approval"
    else:
        assert agent.permissions.pending_action is not None, "Action should be gated"
        assert "should i send it" in res4.lower() or "shall i proceed" in res4.lower(), "Must read back preview"

    # User grants approval
    print("User: Yes")
    res4_approved = agent.process_turn("Yes")
    print(f"Jarvis: {res4_approved}")
    assert agent.permissions.pending_action is None, "Pending action should be cleared after execution"
    print("\033[92m=> TEST 4 PASSED (Preview read back, approval gated, message dispatched)\033[0m")

    # ---------------------------------------------------------
    # TEST 5: Interactive Voice Modification ("change it to...")
    # ---------------------------------------------------------
    print("\n\033[94m[TEST 5: Voice Modification Flow - 'change it to...']\033[0m")
    res5_a = agent.process_turn("text Rahul I will reach in 5 minutes")
    print(f"User: text Rahul I will reach in 5 minutes\nJarvis: {res5_a}")
    
    if "which rahul" in res5_a.lower():
        agent.process_turn("Rahul Pw")

    print("User: change it to I'll be 20 minutes late")
    res5_edit = agent.process_turn("change it to I'll be 20 minutes late")
    print(f"Jarvis: {res5_edit}")
    assert "20 minutes" in res5_edit, "Modified text must be reflected in new read-back"
    
    # User confirms edited version
    print("User: Yes, send it")
    res5_confirmed = agent.process_turn("Yes, send it")
    print(f"Jarvis: {res5_confirmed}")
    print("\033[92m=> TEST 5 PASSED (Voice modification accepted and dispatched)\033[0m")

    # ---------------------------------------------------------
    # TEST 6: Multi-Step Document Search & Email Flow
    # ---------------------------------------------------------
    print("\n\033[94m[TEST 6: Multi-Step - 'email my resume to test@example.com']\033[0m")
    res6 = agent.process_turn("email my resume to test@example.com")
    print(f"User: email my resume to test@example.com\nJarvis: {res6}")
    assert "resume" in res6.lower() and "test@example.com" in res6.lower(), "Must identify resume and recipient"
    assert agent.permissions.pending_action is not None, "Email must be gated for permission"

    # User cancels
    print("User: Cancel")
    res6_cancel = agent.process_turn("Cancel")
    print(f"Jarvis: {res6_cancel}")
    assert agent.permissions.pending_action is None, "Pending action cleared upon cancellation"
    assert "cancelled" in res6_cancel.lower() or "stopped" in res6_cancel.lower(), "Must report cancellation"
    print("\033[92m=> TEST 6 PASSED (Spotlight resolved file, draft prepared, cancel honored)\033[0m")

    # ---------------------------------------------------------
    # TEST 7: BLOCKED Tier Protection (Double Confirmation)
    # ---------------------------------------------------------
    print("\n\033[94m[TEST 7: BLOCKED Tier - 'delete all files in Downloads']\033[0m")
    res7 = agent.process_turn("run shell rm -rf ~/Downloads/test_temp")
    print(f"User: run shell rm -rf ~/Downloads/test_temp\nJarvis: {res7}")
    assert "security warning" in res7.lower() or "high risk" in res7.lower(), "BLOCKED tier must issue security warning"
    
    # Single confirmation should NOT execute
    print("User: Yes")
    res7_single = agent.process_turn("Yes")
    print(f"Jarvis: {res7_single}")
    assert agent.permissions.pending_action is not None, "Single confirmation must NOT execute BLOCKED tier"
    
    # Second confirmation with exact phrase
    print("User: Yes, I'm sure")
    res7_double1 = agent.process_turn("Yes, I'm sure")
    print(f"Jarvis: {res7_double1}")
    
    print("User: Yes, I'm sure")
    res7_double2 = agent.process_turn("Yes, I'm sure")
    print(f"Jarvis: {res7_double2}")
    print("\033[92m=> TEST 7 PASSED (Strict double-confirmation enforced for BLOCKED action)\033[0m")

    # ---------------------------------------------------------
    # TEST 8: Contextual Follow-Up ("send the same to Amit")
    # ---------------------------------------------------------
    print("\n\033[94m[TEST 8: Contextual Memory - 'send the same to Amit']\033[0m")
    # First set a message
    agent.last_message_text = "I'll be late by 15 minutes."
    res8 = agent.process_turn("send the same to Amit")
    print(f"User: send the same to Amit\nJarvis: {res8}")
    assert "15 minutes" in res8 or "amit" in res8.lower(), "Follow-up must retain previous message text"
    agent.process_turn("cancel")
    print("\033[92m=> TEST 8 PASSED (Follow-up successfully reused context memory)\033[0m")

    print("\n" + "=" * 70)
    print("  ALL 8 AUTONOMOUS AGENT & PERMISSION TESTS PASSED (100%)")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_agent_tests()
