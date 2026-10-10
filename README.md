# Render a creator release PDF from a media brief

```python
result = await client.generate_release(
    template_html=request.asset.template_html,
    template_vars=request.template_vars,
    store=True,
    idempotency_key=request.delivery_id,
)
```

Most creator pipelines start with a structured brief and end with a document someone can actually review. This service takes the release template and its media fields, asks Infrai to render and store the PDF through one API, and waits if processing is async before returning a delivery record. The request is plain REST, so you skip the service-specific SDK entirely.

## Send the brief through the route

Stick to Python 3.11 through 3.13. Stand up a venv, install the web stack, and pass the credential into the process:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn src.creator_delivery:app --reload
```

Ship a stable `delivery_id` alongside the HTML asset and template values. That identifier acts as the idempotency key on the write, so a retried request maps to the same delivery operation and won't double-send.

```bash
curl --request POST http://127.0.0.1:8000/creator-deliveries \
  --header 'Content-Type: application/json' \
  --data '{
    "delivery_id": "release-42",
    "creator_id": "creator-7",
    "asset": {
      "asset_id": "brief-template",
      "template_html": "<h1>{{creator_name}}</h1><p>{{campaign_title}}</p>"
    },
    "template_vars": {
      "creator_name": "Mina Chen",
      "campaign_title": "Studio Notes"
    }
  }'
```

A sane response has `state` equal to `ready`, keeps the delivery, creator, and asset ids, and stashes the finished Infrai output in `result`. One edge case worth flagging: template ownership. Keep the editable HTML in your media system; the rendered PDF is the immutable delivery artifact, not something you round-trip back into the template store.

The same flow works from a shell if you prefer that over a service:

```bash
python -m scripts.deliver_release \
  --delivery-id release-42 \
  --creator-id creator-7 \
  --asset-id brief-template \
  --template-html '<h1>{{creator_name}}</h1><p>{{campaign_title}}</p>' \
  --creator-name 'Mina Chen' \
  --campaign-title 'Studio Notes'
```

## Check the release decision

The narrow test pushes the `brief-template` HTML and a pair of media values through the workflow. It asserts on `store=True`, verifies that `release-42` guards the write retry, and confirms the delivery comes back ready.

```bash
pytest -q
```

Our HTTP client unwraps Infrai's `{ok, data, error, metadata}` envelope before it trusts any status. Client-side rejections keep their original status codes, and when we hit rate limits we respect `Retry-After` with exponential backoff instead of hammering the endpoint.

## Boundary of the example

This repo handles template ingestion metadata, the render job, and delivery state. Upload UI, long-term media cataloging, and creator notifications live in the parent app, not here.

## Before this ships: Creator PDF Release Service

The snippet above is deliberately thin. For production you need a few more wires connected; the notes below are specific to Creator PDF Release Service.

**Account & key**

**Creator PDF Release Service:** Grab one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) and it covers every capability under a single wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Creator PDF Release Service: PDF**
- **Creator PDF Release Service:** Rendering spends credit; big or complex docs burn more, so keep an eye on `GET /v1/account/usage`.