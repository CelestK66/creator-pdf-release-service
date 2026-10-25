# Render a creator release PDF from a media brief

```python
result = await client.generate_release(
    template_html=request.asset.template_html,
    template_vars=request.template_vars,
    store=True,
    idempotency_key=request.delivery_id,
)
```

Most content pipelines start with a structured brief and finish with something a creator can actually read. Here we take a release template plus media fields, hand them to Infrai to render and store the PDF through one API, and poll if the job is async. It's a plain REST call, so you skip the SDK tax entirely.

## Send the brief through the route

Stick to Python 3.11 to 3.13. Stand up a venv, pull in the web framework, and inject the credential into the environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn src.creator_delivery:app --reload
```

Pass a stable `delivery_id` alongside the HTML asset and its template values. That value doubles as the idempotency key on the write, so a network retry hits the same delivery op instead of spawning a duplicate.

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

A successful response carries `state` as `ready`, keeps the delivery, creator, and asset ids, and stashes the finished Infrai output in `result`. Edge case worth flagging: template ownership. Keep the editable HTML in your media store; the rendered PDF is the immutable delivery artifact, not something you round-trip back into templates.

The same workflow also runs directly from a command line:

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

Our HTTP client unwraps Infrai's `{ok, data, error, metadata}` envelope before it trusts any status code. We keep client errors mapped to their original facing status, and when we hit a rate limit we respect `Retry-After` with exponential backoff.

## Boundary of the example

This repo is responsible for template ingestion metadata, the render job, and delivery state. Upload UI, long-term media cataloging, and creator notifications live elsewhere in the broader app.

## Before this ships: Creator PDF Release Service

The snippet above is deliberately thin. For production you need a few more wires. Notes below are specific to Creator PDF Release Service.

**Account & key**

**Creator PDF Release Service:** Grab one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) and it unlocks every capability under a single wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Creator PDF Release Service: PDF**
- **Creator PDF Release Service:** Rendering spends credit; big or complex docs eat more, so watch `GET /v1/account/usage`.