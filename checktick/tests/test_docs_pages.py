def test_docs_index_page_renders(client):
    resp = client.get("/docs/")
    assert resp.status_code == 200
    # Should include either the page title or markdown content
    assert b"Documentation" in resp.content


def test_docs_api_page_renders(client):
    resp = client.get("/docs/api/")
    assert resp.status_code == 200
    # The API docs page links to interactive API documentation
    assert b"/api/docs" in resp.content or b"API" in resp.content
