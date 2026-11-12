import gzip
import hashlib
import json
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request


REGISTRY = "http://10.2.0.145:32000"
REPOSITORY = "crosslayer-dashboard-backend"
TAG = "latest"


def request(url, method="GET", data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Registry returned HTTP {error.code}: {detail}") from error


def image_url(path):
    return f"{REGISTRY}/v2/{REPOSITORY}/{path}"


def normalize_location(location):
    parsed = urllib.parse.urlsplit(urllib.parse.urljoin(REGISTRY + "/", location))
    return urllib.parse.urlunsplit(("http", "10.2.0.145:32000", parsed.path, parsed.query, ""))


def upload_blob(data):
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    status, headers, _ = request(image_url("blobs/uploads/"), method="POST")
    if status != 202 or not headers.get("Location"):
        raise RuntimeError(f"Registry did not start a blob upload (HTTP {status}).")

    location = normalize_location(headers["Location"])
    status, headers, _ = request(
        location,
        method="PATCH",
        data=data,
        headers={
            "Content-Type": "application/octet-stream",
            "Content-Range": f"0-{len(data) - 1}",
        },
    )
    if status != 202 or not headers.get("Location"):
        raise RuntimeError(f"Registry did not accept a blob upload (HTTP {status}).")

    location = normalize_location(headers["Location"])
    parsed = urllib.parse.urlsplit(location)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query.append(("digest", digest))
    final_url = urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), "")
    )
    status, _, _ = request(
        final_url,
        method="PUT",
        data=b"",
        headers={"Content-Length": "0"},
    )
    if status != 201:
        raise RuntimeError(f"Registry did not finalize a blob upload (HTTP {status}).")
    return digest


def main(archive_path):
    with tarfile.open(archive_path, "r") as archive:
        manifest_entry = next(
            item for item in json.load(archive.extractfile("manifest.json"))
            if any(tag.endswith(f":{TAG}") for tag in item.get("RepoTags", []))
        )
        config_data = archive.extractfile(manifest_entry["Config"]).read()
        config_digest = upload_blob(config_data)
        print("Uploaded image config.")

        layers = []
        for layer_name in manifest_entry["Layers"]:
            raw_layer = archive.extractfile(layer_name).read()
            layer_data = (
                raw_layer
                if raw_layer.startswith(b"\x1f\x8b")
                else gzip.compress(raw_layer, compresslevel=6, mtime=0)
            )
            digest = upload_blob(layer_data)
            layers.append(
                {
                    "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                    "size": len(layer_data),
                    "digest": digest,
                }
            )
            print(f"Uploaded image layer {len(layers)}/{len(manifest_entry['Layers'])}.")

        manifest = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "config": {
                "mediaType": "application/vnd.docker.container.image.v1+json",
                "size": len(config_data),
                "digest": config_digest,
            },
            "layers": layers,
        }
        status, _, _ = request(
            image_url(f"manifests/{TAG}"),
            method="PUT",
            data=json.dumps(manifest, separators=(",", ":")).encode(),
            headers={"Content-Type": "application/vnd.docker.distribution.manifest.v2+json"},
        )
        if status != 201:
            raise RuntimeError(f"Registry did not accept the image manifest (HTTP {status}).")
        print(f"Published {REGISTRY}/{REPOSITORY}:{TAG}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: publish-image.py <docker-save-archive.tar>")
    main(sys.argv[1])
