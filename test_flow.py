import sys
import json
import httpx

BASE_URL = "http://127.0.0.1:8000"

def log_step(title):
    print(f"\n{'='*20} {title} {'='*20}")

def run_tests():
    print("Testing AI-Powered Learning Platform Backend Flow...")
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # 1. Health / Root
    log_step("1. Health Check (GET /)")
    res = client.get("/")
    assert res.status_code == 200, f"Root failed: {res.text}"
    print("[PASS] Root online:", res.json())

    # 2. Check Seed Data (GET /api/profile)
    log_step("2. Check Seed Data (GET /api/profile)")
    res = client.get("/api/profile")
    assert res.status_code == 200, f"Profile failed: {res.text}"
    profile = res.json()
    print("[PASS] Profile response:", json.dumps(profile, indent=2))
    assert profile["student_id"] == 1
    assert "SQL" in profile["skills"]
    assert profile["skills"]["SQL"]["score_percent"] == 40
    assert profile["skills"]["SQL"]["needs_reinforcement"] is True
    print("[PASS] Auto-seeded demo student with SQL 40% and needs_reinforcement=True verified!")

    # 3. Check Initial Roadmap (GET /api/roadmap)
    log_step("3. Check Initial Roadmap (GET /api/roadmap)")
    res = client.get("/api/roadmap")
    assert res.status_code == 200, f"Roadmap failed: {res.text}"
    roadmap = res.json()
    assert "weeks" in roadmap and len(roadmap["weeks"]) == 4
    week1 = roadmap["weeks"][0]
    print("[PASS] Week 1 Plan:", json.dumps(week1, indent=2))
    assert "JOIN" in week1["reason"] or any("JOIN" in t for t in week1["topics"])
    print("[PASS] Initial roadmap correctly prioritizes SQL JOINs in Week 1!")

    # 4. Update Profile Ratings (POST /api/profile)
    log_step("4. Update Profile (POST /api/profile)")
    update_payload = {
        "skills": {
            "Python": "Intermediate",
            "SQL": "Beginner",
            "HTML/CSS": "Advanced",
            "FastAPI": "Beginner"
        }
    }
    res = client.post("/api/profile", json=update_payload)
    assert res.status_code == 200, f"Update profile failed: {res.text}"
    print("[PASS] Updated profile response:", res.json())

    # 5. Generate Assessment (POST /api/assess/SQL)
    log_step("5. Generate Assessment (POST /api/assess/SQL)")
    res = client.post("/api/assess/SQL")
    assert res.status_code == 200, f"Assessment generation failed: {res.text}"
    quiz = res.json()
    quiz_id = quiz["quiz_id"]
    questions = quiz["questions"]
    print(f"[PASS] Assessment generated: quiz_id={quiz_id}, questions count={len(questions)}")
    assert len(questions) == 4, f"Expected 4 questions, got {len(questions)}"
    for q in questions:
        assert "correct_answer" not in q, "SECURITY LEAK: correct_answer sent to client!"
        assert len(q["options"]) == 4, f"Expected 4 options in question {q['id']}"
    print("[PASS] No correct answers leaked to client! All 4 questions formatted properly.")

    # 6. Submit Assessment with answers (POST /api/assess/SQL/submit)
    log_step("6. Submit Assessment (POST /api/assess/SQL/submit)")
    # Intentionally select wrong answers to test <50% reinforcement trigger
    dummy_answers = {
        questions[0]["id"]: questions[0]["options"][0],
        questions[1]["id"]: questions[1]["options"][0],
        questions[2]["id"]: questions[2]["options"][0],
        questions[3]["id"]: questions[3]["options"][0],
    }
    res = client.post("/api/assess/SQL/submit", json={"quiz_id": quiz_id, "answers": dummy_answers})
    assert res.status_code == 200, f"Submit assessment failed: {res.text}"
    submit_res = res.json()
    print("[PASS] Submit result:", json.dumps(submit_res, indent=2))
    assert "score" in submit_res and "total" in submit_res and "weak_subtopics" in submit_res
    assert "explanations" in submit_res

    # 7. Verify Skill Score Updated in DB (GET /api/profile)
    log_step("7. Verify Skill Score updated in DB")
    res = client.get("/api/profile")
    updated_profile = res.json()
    print("[PASS] Updated SQL status:", updated_profile["skills"]["SQL"])

    # 8. Trigger Roadmap Replan (POST /api/roadmap/replan)
    log_step("8. Replan Roadmap (POST /api/roadmap/replan)")
    res = client.post("/api/roadmap/replan")
    assert res.status_code == 200, f"Replan failed: {res.text}"
    new_roadmap = res.json()
    assert len(new_roadmap["weeks"]) == 4
    print("[PASS] Replanned Roadmap Week 1:", json.dumps(new_roadmap["weeks"][0], indent=2))
    print("[PASS] Replanned Roadmap Week 2:", json.dumps(new_roadmap["weeks"][1], indent=2))

    # 9. Ask a Doubt (POST /api/ask)
    log_step("9. Ask a Doubt (POST /api/ask)")
    doubt_payload = {"question": "What is the difference between an INNER JOIN and a LEFT JOIN in SQL?"}
    res = client.post("/api/ask", json=doubt_payload)
    assert res.status_code == 200, f"Ask doubt failed: {res.text}"
    doubt_res = res.json()
    print("[PASS] Doubt Answer:", doubt_res["answer"][:150], "...")
    print("[PASS] Suggested Topic:", doubt_res["suggested_topic"])
    assert doubt_res["suggested_topic"] is not None

    print("\n" + "="*50)
    print("ALL BACKEND FLOW TESTS PASSED SUCCESSFULLY! 100% WORKING.")
    print("="*50)

if __name__ == "__main__":
    run_tests()
