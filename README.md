# BDDS Performance Statistics — BlueCat Gateway workflow

Real-time DNS queries-per-second (QPS) and DHCP leases-per-second (LPS) for every BDDS
server managed by a BAM, shown as a Gateway UI page. Data comes from BAM's built-in
Prometheus (not from each BDDS's `:10048` exporter directly). The Prometheus host is read
from this Gateway's own BAM connection at runtime — it is never hardcoded — so the same
package works against any Gateway/BAM pairing.

See [docs/README.md](docs/README.md) for the full workflow doc (REST endpoints, UI page,
dependencies, change log).

## How to import into BlueCat Gateway

1. Download the packaged `bdds_qps_ui-<version>.tar.gz` from this repo's
   [Releases](../../releases) page (or build it yourself — see below).
2. In Gateway, go to **Administration > Workflow management**.
3. If a previous version of `bdds_qps_ui` is already installed, delete it first.
4. Click **Import workflow** and select the `bdds_qps_ui-<version>.tar.gz` file.
5. Gateway needs to restart its app process to load the new workflow code — this happens
   automatically as part of the import and takes a few seconds, during which the Gateway
   UI is briefly unavailable to all users.
6. Once it's back, open **BDDS Performance Statistics** in the left nav and confirm data
   loads for your BDDS servers.

### Building the tar.gz yourself

Gateway expects the archive to contain a single top-level `bdds_qps_ui/` directory (this
repo's contents are flattened to the repo root so GitHub renders this README directly, so
the layout isn't upload-ready as-is):

```bash
git archive --prefix=bdds_qps_ui/ -o bdds_qps_ui.tar.gz HEAD -- . ':!README.md' ':!.gitignore'
```
