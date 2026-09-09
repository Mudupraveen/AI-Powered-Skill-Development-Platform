import json
import httpx

BASE_URL = "http://127.0.0.1:8000"

def banner(title):
    print("\n" + "=" * 65)
    print(f"  >>> {title}")
    print("=" * 65)

def simulate_full_user_flow():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # 1. SET SKILLS (Onboarding flow)
    banner("STEP 1: SET SKILLS (POST /api/profile)")
    profile_payload = {
        "skills": {
            "Python": "Intermediate",
            "SQL": "Beginner",
            "HTML/CSS": "Intermediate",
            "FastAPI": "Beginner"
        }
    }
    r = client.post("/api/profile", json=profile_payload)
    assert r.status_code == 200
    print("[SUCCESS] Skills set successfully:", r.json())

    # 2. GET QUIZ (Assessment flow)
    banner("STEP 2: GET QUIZ (POST /api/assess/SQL)")
    r = client.post("/api/assess/SQL")
    assert r.status_code == 200
    quiz_data = r.json()
    quiz_id = quiz_data["quiz_id"]
    questions = quiz_data["questions"]
    print(f"[SUCCESS] Quiz generated: ID={quiz_id}, Total Questions={len(questions)}")
    for i, q in enumerate(questions, 1):
        print(f"  Q{i}: {q['text']} (Tag: {q['topic_tag']})")
        print(f"      Options: {q['options']}")

    # 3. SUBMIT QUIZ (Submitting answers to assess knowledge gaps)
    banner("STEP 3: SUBMIT QUIZ (POST /api/assess/SQL/submit)")
    # Submit first option for each
    answers = {q["id"]: q["options"][0] for q in questions}
    r = client.post("/api/assess/SQL/submit", json={"quiz_id": quiz_id, "answers": answers})
    assert r.status_code == 200
    submit_result = r.json()
    print(f"[SUCCESS] Quiz submitted. Score: {submit_result['score']}/{submit_result['total']} ({submit_result['score_percent']}%)")
    print(f"          Weak subtopics detected: {submit_result['weak_subtopics']}")
    print(f"          Explanations received: {list(submit_result['explanations'].keys())}")

    # 4. SEE UPDATED SKILL % (Dashboard verification)
    banner("STEP 4: SEE UPDATED SKILL % (GET /api/profile)")
    r = client.get("/api/profile")
    assert r.status_code == 200
    current_profile = r.json()
    sql_skill = current_profile["skills"]["SQL"]
    print(f"[SUCCESS] Updated SQL skill in DB:")
    print(f"          Score %: {sql_skill['score_percent']}%")
    print(f"          Needs Reinforcement: {sql_skill['needs_reinforcement']}")
    print(f"          Last Updated: {sql_skill['last_updated']}")

    # 5. SEE ROADMAP (Dashboard roadmap timeline)
    banner("STEP 5: SEE ROADMAP (GET /api/roadmap)")
    r = client.get("/api/roadmap")
    assert r.status_code == 200
    initial_roadmap = r.json()
    print(f"[SUCCESS] Current Roadmap (4 Weeks):")
    for w in initial_roadmap["weeks"]:
        print(f"  Week {w['week']}: {w['topics']}")
        print(f"         Reason: {w['reason']}")

    # 6. ASK A ROADMAP REPLAN (Planner Agent execution)
    banner("STEP 6: ASK A ROADMAP REPLAN (POST /api/roadmap/replan)")
    r = client.post("/api/roadmap/replan")
    assert r.status_code == 200
    replanned_roadmap = r.json()
    print("[SUCCESS] Replan executed successfully:")
    week1 = replanned_roadmap["weeks"][0]
    print(f"  Week 1 (Reinforcement focus): {week1['topics']}")
    print(f"         Reason: {week1['reason']}")

    # 7. ASK A DOUBT (Doubt Tutor flow)
    banner("STEP 7 & 8: ASK A DOUBT & GET EXPLANATION (POST /api/ask)")
    doubt_query = "What is the difference between an INNER JOIN and a LEFT JOIN in SQL?"
    print(f"Student question: '{doubt_query}'")
    r = client.post("/api/ask", json={"question": doubt_query})
    assert r.status_code == 200
    doubt_response = r.json()
    suggested_topic = doubt_response["suggested_topic"]
    print(f"[SUCCESS] Explanation received:\n{doubt_response['answer'][:250]}...\n")
    print(f"[SUCCESS] AI Suggested Follow-up Topic: '{suggested_topic}'")

    # 9. TAKE FOLLOW-UP QUIZ (Practice flow from Doubt page)
    banner(f"STEP 9: TAKE FOLLOW-UP QUIZ FOR '{suggested_topic}'")
    r = client.post(f"/api/assess/{suggested_topic}")
    assert r.status_code == 200
    followup_quiz = r.json()
    print(f"[SUCCESS] Follow-up quiz received: ID={followup_quiz['quiz_id']} (4 questions)")

    # Submit follow-up quiz
    f_answers = {q["id"]: q["options"][0] for q in followup_quiz["questions"]}
    r = client.post(f"/api/assess/{suggested_topic}/submit", json={"quiz_id": followup_quiz["quiz_id"], "answers": f_answers})
    assert r.status_code == 200
    f_submit_result = r.json()
    print(f"[SUCCESS] Follow-up quiz submitted. Score: {f_submit_result['score']}/{f_submit_result['total']}")

    # 10. SEE ROADMAP UPDATE AGAIN
    banner("STEP 10: SEE ROADMAP UPDATE AGAIN (POST /api/roadmap/replan)")
    r = client.post("/api/roadmap/replan")
    assert r.status_code == 200
    final_roadmap = r.json()
    print(f"[SUCCESS] Final updated roadmap generated with latest assessment insights:")
    for w in final_roadmap["weeks"]:
        print(f"  Week {w['week']}: {w['topics']}")

    print("\n" + "#" * 65)
    print("  ALL 10 STEPS OF THE USER FLOW COMPLETED SUCCESSFULLY!")
    print("#" * 65)

if __name__ == "__main__":
    simulate_full_user_flow()
