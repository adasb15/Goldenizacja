from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import router


def test_file_line_count_csv() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    payload = "col1,col2\n1,a\n2,b\n3,c\n"
    response = client.post(
        "/files/line-count",
        files={"file": ("test.csv", payload, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json() == {"filename": "test.csv", "line_count": 4}


def test_file_line_count_reject_non_csv() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    payload = "wiersz 1\nwiersz 2\n"
    response = client.post(
        "/files/line-count",
        files={"file": ("test.txt", payload, "text/plain")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Only CSV files are supported."}
