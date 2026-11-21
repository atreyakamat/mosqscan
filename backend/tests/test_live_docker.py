import httpx
import time
import subprocess

BASE_URL = "http://localhost:8000"

def run_tests():
    print("--- 1. Testing Unauthorized Request Rejection ---")
    res = httpx.get(f"{BASE_URL}/api/v1/auth/me")
    print(f"Status: {res.status_code}, Body: {res.json()}")
    assert res.status_code == 401

    print("\n--- 2. Testing Registration (User 1) ---")
    ts = int(time.time())
    user1_data = {
        "username": f"researcher1_{ts}",
        "email": f"field_researcher_1_{ts}@vectora.org",
        "password": "StrongPassword123!"
    }
    res = httpx.post(f"{BASE_URL}/api/v1/auth/register", json=user1_data)
    print(f"Status: {res.status_code}, Body: {res.json()}")
    assert res.status_code == 201
    user1_id = res.json()["id"]

    print("\n--- 3. Testing Login (User 1) ---")
    login_data = {
        "email": user1_data["email"],
        "password": "StrongPassword123!"
    }
    res = httpx.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    print(f"Status: {res.status_code}")
    assert res.status_code == 200
    login_json = res.json()
    access_token_1 = login_json["access_token"]
    headers_1 = {"Authorization": f"Bearer {access_token_1}"}

    print("\n--- 4. Testing User Profile (User 1) ---")
    res = httpx.get(f"{BASE_URL}/api/v1/auth/me", headers=headers_1)
    user_email = res.json()["email"]
    print(f"Status: {res.status_code}, Email: {user_email}")
    assert res.status_code == 200
    assert user_email == user1_data["email"]

    print("\n--- 5. Testing Adult Mosquito Identification ---")
    with open("model-registry/golden-tests/images/aedes_01.jpg", "rb") as f:
        files = {"file": ("aedes_01.jpg", f, "image/jpeg")}
        res = httpx.post(f"{BASE_URL}/api/v1/adult/submit", headers=headers_1, files=files)
    print(f"Status: {res.status_code}, Body: {res.json()}")
    assert res.status_code == 201
    adult_resp = res.json()
    result = adult_resp["result"]
    print(f"Top score genus: {max(result['all_scores'], key=result['all_scores'].get)}, Confidence: {result['confidence']}, Model Artifact: {result['model_artifact']}")
    assert max(result['all_scores'], key=result['all_scores'].get) == "aedes"
    assert result["model_artifact"] in ("vectora_candidate_exp_b.onnx", "vectora_v3_fp32.onnx")

    print("\n--- 6. Testing Larvae Job Submission & Celery Worker Processing ---")
    temp_vid = "/tmp/live_docker_test.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=3.5:size=640x480:rate=30", "-c:v", "libx264", "-pix_fmt", "yuv420p", temp_vid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    with open(temp_vid, "rb") as f:
        files = {"file": ("live_docker_test.mp4", f, "video/mp4")}
        res = httpx.post(f"{BASE_URL}/api/v1/larvae/submit", headers=headers_1, files=files)
    print(f"Status: {res.status_code}, Body: {res.json()}")
    assert res.status_code == 202
    job_id = res.json()["job_id"]
    submission_id = res.json()["submission_id"]

    print(f"\n--- 7. Polling Job Status for Job {job_id} ---")
    final_status = None
    for i in range(25):
        res = httpx.get(f"{BASE_URL}/api/v1/larvae/jobs/{job_id}", headers=headers_1)
        job_data = res.json()
        final_status = job_data["status"]
        print(f"Poll {i+1}: status = {final_status}")
        if final_status.upper() in ("COMPLETED", "FAILED"):
            print(f"Final Job Data: {job_data}")
            break
        time.sleep(1)
    assert final_status.upper() == "COMPLETED"

    # Also test retrieving submission result
    res = httpx.get(f"{BASE_URL}/api/v1/larvae/submissions/{submission_id}", headers=headers_1)
    print(f"Submission status: {res.status_code}, Body: {res.json()}")
    assert res.status_code == 200

    print("\n--- 8. Testing Cross-User Isolation (User 2) ---")
    ts2 = int(time.time()) + 1
    user2_data = {
        "username": f"researcher2_{ts2}",
        "email": f"field_researcher_2_{ts2}@vectora.org",
        "password": "StrongPassword456!"
    }
    res = httpx.post(f"{BASE_URL}/api/v1/auth/register", json=user2_data)
    assert res.status_code == 201

    res = httpx.post(f"{BASE_URL}/api/v1/auth/login", json={"email": user2_data["email"], "password": "StrongPassword456!"})
    assert res.status_code == 200
    headers_2 = {"Authorization": f"Bearer {res.json()['access_token']}"}

    # User 2 attempts to fetch User 1's larvae job
    res = httpx.get(f"{BASE_URL}/api/v1/larvae/jobs/{job_id}", headers=headers_2)
    print(f"User 2 fetching User 1 job - Status: {res.status_code}, Body: {res.json()}")
    assert res.status_code == 403

    # User 2 attempts to fetch User 1's adult submission
    res = httpx.get(f"{BASE_URL}/api/v1/adult/submissions/{adult_resp['id']}", headers=headers_2)
    print(f"User 2 fetching User 1 adult submission - Status: {res.status_code}, Body: {res.json()}")
    assert res.status_code == 403

    print("\nALL LIVE DOCKER API TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
