# Viva Preparation

Verification and viva is 1.5 of 10 marks, and the rubric wants "clear answers to
questions". Starred questions are the ones most likely to be asked, because they are the
ones that separate someone who ran the commands from someone who understands them.

Read the Jenkinsfile and `k8s/deployment.yaml` with this open beside you. Do not memorise
these answers word for word. Say them in your own words, because an examiner can tell.

---

## The project itself

**What does your application do?**
It is a student grade management system. It holds a semester's course results for a set
of students, converts raw marks into letter grades and grade points on a ten point scale,
computes a credit weighted SGPA, and shows the ranked result table. There is also a JSON
API on `/api/students` and a `/health` endpoint.

**Where is the data stored?**
In memory, in `app/data.py`. That was deliberate. The app is stateless, which is why two
replicas can sit behind one Service with no shared database and no volume. If I added
persistence I would need a StatefulSet or a PersistentVolumeClaim, and on Minikube that
means a hostPath volume.

**What is actually tested?**
57 tests in `tests/`. `test_grades.py` covers the grading logic: every band boundary, the
credit weighting arithmetic, and rejection of bad input such as negative marks, marks over
100, non-numeric marks and zero credits. `test_api.py` hits each route through Flask's
test client and checks status codes and payloads.

**Why test boundaries like 89 and 90?**
Because off-by-one errors in banding are the realistic bug. A student scoring exactly 90
must get O, not A+. Testing the middle of a band would never catch that.

---

## Docker

**\* What is the difference between an image and a container?**
An image is a read-only, layered filesystem plus metadata about how to start it. A
container is a running instance of an image with a writable layer on top. One image, many
containers.

**\* Walk me through your Dockerfile.**
Start from `python:3.12-slim` to keep the image small. Set `PYTHONUNBUFFERED` so logs
reach `kubectl logs` immediately instead of sitting in a buffer. Copy `requirements.txt`
and install **before** copying the source, so that changing application code reuses the
cached dependency layer. Copy the app. Create a non-root user and switch to it. Expose
8080 and run gunicorn.

**\* Why copy requirements.txt separately instead of copying everything at once?**
Docker caches each layer and invalidates every layer after the first one that changes. If
I copied the source first, every one-line code change would reinstall every dependency.
Splitting it means a code change only rebuilds the last layer, so builds go from minutes
to seconds.

**Why not the Flask development server?**
It is single threaded and explicitly not for production. Gunicorn runs multiple workers
and handles concurrent requests properly.

**Why a non-root user?**
If someone escapes the application into the container, they land as an unprivileged user
rather than root. It limits the blast radius.

**What is `.dockerignore` for?**
It keeps files out of the build context sent to the daemon. It makes builds faster, and
it stops things like `.git` and local environment files ending up inside the image.

**Why is `pytest` not in the image?**
`requirements.txt` has runtime dependencies only. Test tooling is in
`requirements-dev.txt`, which Jenkins installs but the Dockerfile never touches. The
shipped container has no test framework in it.

---

## Jenkins and the pipeline

**\* What are the stages and what does each do?**
Checkout pulls the commit from GitHub. Build and Test makes a virtualenv, installs
dependencies, runs flake8 and runs pytest. Docker Build builds the image and tags it with
the build number. Push Image logs in to Docker Hub and pushes. Deploy applies the
Kubernetes manifests and pins the image to this build's tag. Verify prints pods,
deployment, service and rollout history, and curls the Service from inside the cluster.

**\* How are your Docker Hub credentials protected?**
They are stored in Jenkins credentials with the ID `dockerhub-creds` and injected at run
time by `withCredentials`. They are never in the repository. Two further details: the
shell block is in **single quotes**, so Groovy does not interpolate the secret into the
script text where it could be logged; and the login uses `--password-stdin` rather than
`-p`, so the token never appears in the process list. Jenkins also masks the value in
console output.

**What would happen if you used double quotes on that shell block?**
Groovy would substitute the password into the script string before the shell ever ran.
That expanded string can end up in logs and in error messages. It is a real leak.

**Why a virtualenv in the build stage?**
So the job does not install packages into the system Python. Two jobs with conflicting
dependency versions would otherwise fight each other.

**Declarative or scripted pipeline, and why?**
Declarative. It has a fixed structure that Jenkins validates, built in `post` blocks for
success and failure handling, and it is far easier to read. Scripted gives more
programmatic freedom, which I did not need.

**What does the `post { failure { ... } }` block do?**
On a failed build it dumps pod status, the deployment description and recent container
logs into the console, so I can diagnose from the build page without SSHing in.

**Why poll SCM instead of a webhook?**
A webhook needs GitHub to make an inbound connection to my EC2 instance. My security
group only allows my own IP, on purpose. Polling works from behind that restriction. On a
real setup with a public Jenkins, a webhook is better because it is instant and does not
waste cycles.

---

## Registry

**Why push to Docker Hub at all, when Docker and Minikube are on the same machine?**
Because Kubernetes pulls images from a registry, not from the local Docker daemon. They
are separate storage. Pushing to a registry is also what makes the build portable, so the
same image could be pulled by a real cluster.

**\* Why tag with the build number instead of `latest`?**
This is the important one. If every build pushed `:latest` and the Deployment asked for
`:latest`, the pod spec would be byte-for-byte identical between builds. Kubernetes
compares the desired spec to the current one, sees no difference, and does nothing. The
new code would sit in the registry and never deploy. Tagging with `$BUILD_NUMBER` changes
the spec, which triggers a rollout. I push `:latest` as well, but only as a convenience
pointer.

**What is `imagePullPolicy: Always` doing?**
Forcing a registry pull rather than using a cached image on the node. With `IfNotPresent`
and a reused tag, the node would serve the stale cached layer. Combined with unique tags
it is belt and braces, and it is what makes the redeployment reliable.

---

## Kubernetes

**\* What is the difference between a Pod, a ReplicaSet and a Deployment?**
A Pod is one or more containers sharing a network namespace, and it is the smallest
schedulable unit. A ReplicaSet keeps a stated number of identical Pods running. A
Deployment manages ReplicaSets and gives you declarative updates and rollback: on a
change it creates a new ReplicaSet and scales it up while scaling the old one down.

**\* How does the Service know which Pods to send traffic to?**
By label selector. The Service has `selector: app: cca2-app`, and the Pod template
carries the matching label. It is not wired by name or by IP. Pods come and go and get new
IPs; the label is the stable link.

**Explain the three ports in your Service.**
`port: 80` is what other things inside the cluster call. `targetPort: 8080` is the port
the container actually listens on. `nodePort: 30080` is the port opened on the node
itself so traffic can get in from outside the cluster.

**Why NodePort and not LoadBalancer?**
LoadBalancer asks the cloud provider to provision an actual load balancer. Minikube is not
a cloud provider, so a LoadBalancer Service would sit in `Pending` forever. NodePort is
the right choice for a local cluster. In production on EKS I would use LoadBalancer or an
Ingress.

**Why are your probes TCP rather than HTTP?**
A TCP probe succeeds as soon as the port accepts a connection. An HTTP probe checks a
specific path, and if that path returned 404 the pod would never become Ready and the
rollout would hang. The app does have `/health`, so an HTTP probe against that path would
also be correct and slightly stricter. TCP was the safer default.

**Difference between readiness and liveness?**
Readiness decides whether the Pod receives traffic from the Service. Liveness decides
whether the kubelet restarts the container. A slow-starting app should be not-ready, not
killed, which is why the liveness probe has a longer initial delay.

**What does `maxUnavailable: 0` give you?**
During a rolling update Kubernetes brings a new Pod up and waits for it to be Ready before
taking an old one down, so the app stays reachable throughout. The cost is briefly needing
capacity for an extra Pod.

**\* How would you roll back?**
`kubectl rollout undo deployment/cca2-app -n cca2`. The Deployment keeps previous
ReplicaSets, capped by `revisionHistoryLimit: 5`, so it scales the previous one back up.

**Why a separate namespace?**
It scopes the objects, so `kubectl delete namespace cca2` cleans up everything at once and
my objects cannot collide with anything else on the cluster.

---

## AWS and the environment

**\* Why does the `jenkins` user need to be in the `docker` group?**
Jenkins runs as the `jenkins` system user, and the Docker socket is owned by the `docker`
group. Without membership, every `docker` command in the pipeline fails with permission
denied on `/var/run/docker.sock`.

**And the security implication of that?**
It is effectively root. Anyone who can run a Jenkins job can mount the host filesystem
into a privileged container. On a real system I would isolate builds onto agents rather
than running them on the controller.

**\* Why did you start Minikube as the `jenkins` user?**
Minikube writes its kubeconfig and certificates into the starting user's home directory.
Started as `ubuntu`, they land in `/home/ubuntu`, which `jenkins` cannot read, and the
deploy stage fails with a connection refused to localhost:8080. Starting it as `jenkins`
puts them in `/var/lib/jenkins`, where the pipeline finds them.

**Why not `t2.micro`?**
Jenkins, the Docker daemon and a Minikube node need more than 1 GB between them. It fails
partway through the Docker build when memory runs out.

**Why is your security group restricted to your own IP?**
An internet-facing Jenkins on 8080 gets scanned and attacked quickly. There is no reason
for anyone but me to reach it.

**What is Minikube and how does it differ from a real cluster?**
A single-node Kubernetes cluster for local development, here running the control plane and
the kubelet inside a Docker container. A real cluster has multiple nodes, real load
balancer integration, and separated control plane. The API and the manifests are the same,
which is the point.

---

## Questions about the pipeline as a whole

**What is CI and what is CD?**
Continuous integration is merging and automatically building and testing every change, so
breakage surfaces in minutes. Continuous delivery or deployment extends that through to
getting the artifact into an environment automatically. This pipeline does both: it tests
on every push and deploys the result.

**What breaks if the test stage fails?**
The build stops there. Declarative pipeline stages run in order and a non-zero exit fails
the stage, so a broken commit never gets built into an image or deployed. `set -e` in the
shell blocks ensures a failing command inside a multi-line script does not get swallowed.

**\* What would you change to make this production ready?**
Several things. Move builds onto dedicated agents instead of the Jenkins controller. Scan
the image for vulnerabilities before pushing. Add staging and production environments with
a manual approval gate. Replace NodePort with an Ingress and TLS. Use a real registry with
immutable tags. Replace in-memory data with a managed database. Add resource monitoring
and alerting. And run Jenkins itself behind a reverse proxy with HTTPS rather than plain
HTTP on 8080.

**If I changed one line of CSS, which stages would re-run and how long would it take?**
All of them, but quickly. The dependency layer is cached, so the Docker build only redoes
the final copy. The slow parts are the registry push and waiting for the rollout.

---

## Be ready to actually do these live

- Open the Jenkinsfile and point at the stage being asked about
- `kubectl get pods -n cca2 -o wide`
- `kubectl describe deployment cca2-app -n cca2`
- `kubectl rollout history deployment/cca2-app -n cca2`
- `kubectl get deploy cca2-app -n cca2 -o jsonpath='{.spec.template.spec.containers[0].image}'`
- `kubectl rollout undo deployment/cca2-app -n cca2` then redeploy
- Show the Docker Hub page with both tags
- Show the Jenkins credential entry and point out that the secret is not visible

One honest note. If you are asked something you do not know, say so and say what you would
check. "I'm not certain, I'd look at the pod events with `kubectl describe`" scores better
than a confident wrong answer, which invites three harder follow-ups.
