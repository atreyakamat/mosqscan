"""Dashboard and history management tests."""
from __future__ import annotations

import io
from tests.conftest import create_test_image


def test_dashboard_stats_user_isolation(client, test_user, second_user):
    # User 1 submits 2 images
    for _ in range(2):
        img_bytes = create_test_image()
        client.post(
            "/api/v1/adult/submit",
            headers=test_user["headers"],
            files={"file": ("mosquito.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        )

    # User 2 submits 1 image
    img_bytes = create_test_image()
    client.post(
        "/api/v1/adult/submit",
        headers=second_user["headers"],
        files={"file": ("mosquito.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )

    # Check User 1 stats: total must be 2, adult must be 2
    res1 = client.get("/api/v1/dashboard/stats", headers=test_user["headers"])
    assert res1.status_code == 200
    stats1 = res1.json()
    assert stats1["total_submissions"] == 2
    assert stats1["adult_submissions"] == 2
    assert stats1["larvae_submissions"] == 0

    # Check User 2 stats: total must be 1, not 3
    res2 = client.get("/api/v1/dashboard/stats", headers=second_user["headers"])
    assert res2.status_code == 200
    stats2 = res2.json()
    assert stats2["total_submissions"] == 1
    assert stats2["adult_submissions"] == 1


def test_submissions_history_and_deletion(client, test_user):
    # Submit image
    img_bytes = create_test_image()
    sub_res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("mosquito.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    sub_id = sub_res.json()["id"]

    # Retrieve unified list
    list_res = client.get("/api/v1/submissions?type=adult", headers=test_user["headers"])
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(item["id"] == sub_id for item in items)

    # Delete submission
    del_res = client.delete(f"/api/v1/submissions/{sub_id}", headers=test_user["headers"])
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Retrieve again: must be 404
    detail_res = client.get(f"/api/v1/submissions/{sub_id}", headers=test_user["headers"])
    assert detail_res.status_code == 404


def test_submissions_history_search_filter(client, test_user):
    """Search query must filter matching submission records and exclude non-matching."""
    img_bytes = create_test_image()
    sub_res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("special_specimen_alpha.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    sub_id = sub_res.json()["id"]

    # Search for matching term
    res_match = client.get("/api/v1/submissions?search=special_specimen_alpha", headers=test_user["headers"])
    assert res_match.status_code == 200
    items = res_match.json()["items"]
    assert any(item["id"] == sub_id for item in items)

    # Search for non-matching term
    res_no_match = client.get("/api/v1/submissions?search=completely_nonexistent_xyz", headers=test_user["headers"])
    assert res_no_match.status_code == 200
    assert len(res_no_match.json()["items"]) == 0
