# Student Grade Management System: CI/CD Pipeline and Kubernetes Deployment

**CCA 2 submission**
Course: Cloud Computing and DevOps, TY CSE
Name: `<YOUR NAME>`
Roll number: `<YOUR ROLL NUMBER>`
Repository: `<YOUR GITHUB URL>`
Docker Hub image: `<YOUR DOCKERHUB USERNAME>/cca2-app`

---

## 1. The project

The application is a student grade management system written in Python with Flask. It
holds a semester's course results for a set of students and turns raw marks into
something useful: a letter grade and grade point for each course, a credit weighted SGPA
for each student, and a ranked result table. Alongside the web pages it exposes a small
JSON API and a health endpoint.

The grading logic lives in `app/grades.py`, deliberately separated from anything to do
with Flask so it can be unit tested on its own. That separation is what makes the test
stage of the pipeline meaningful rather than decorative.

| Route | Purpose |
|---|---|
| `/` | Ranked result table for all students |
| `/student/<roll_no>` | Per course breakdown for one student |
| `/api/students` | All records as JSON |
| `/api/students/<roll_no>` | One record as JSON |
| `/api/grade/<score>` | Convert a raw score to grade and points |
| `/health` | Liveness check |

The application keeps its data in memory rather than in a database. This was a design
decision, not a shortcut: a stateless application can run as two identical replicas behind
a single Service with no shared storage and no coordination. Adding a database would have
meant a StatefulSet or a PersistentVolumeClaim and would have added nothing to what this
assignment is assessing.

### Repository layout

```
.
├── app/
│   ├── grades.py            grade computation, no framework dependencies
│   ├── data.py              seed records
│   ├── main.py              Flask routes and the version banner
│   ├── templates/           Jinja2 templates
│   └── static/style.css
├── tests/
│   ├── test_grades.py       unit tests for the grading logic
│   └── test_api.py          route level integration tests
├── k8s/
│   ├── namespace.yaml
│   ├── deployment.yaml
│   └── service.yaml
├── docs/                    setup guide, screenshot checklist, viva notes
├── screenshots/             evidence of each pipeline run
├── Dockerfile
├── .dockerignore
├── Jenkinsfile
├── requirements.txt         runtime dependencies, these go in the image
└── requirements-dev.txt     test and lint tooling, deliberately kept out of the image
```

### Tests

There are 57 tests. `test_grades.py` checks every grade band boundary, the credit
weighted SGPA arithmetic, and rejection of invalid input such as negative marks, marks
above 100, non-numeric marks and zero or negative credits. Boundary cases are tested
specifically, because an off-by-one in the banding is the realistic bug: a student scoring
exactly 90 must receive O and not A+. `test_api.py` exercises each route through the Flask
test client and asserts on status codes and response payloads.

Run them locally with:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

---

## 2. The pipeline

Defined in `Jenkinsfile` as a declarative pipeline. Six stages, no manual steps between
them.

| # | Stage | What happens |
|---|---|---|
| 1 | Checkout | Jenkins pulls the latest commit from GitHub and prints the commit hash, branch and message |
| 2 | Build and Test | Creates a virtualenv, installs dependencies, runs flake8, runs pytest and publishes the JUnit results to the build page |
| 3 | Docker Build | Builds the image from the Dockerfile, tagged with the Jenkins build number and also with `latest` |
| 4 | Push Image | Logs in to Docker Hub using a stored credential and pushes both tags |
| 5 | Deploy to Minikube | Applies the namespace, Deployment and Service manifests, pins the container image to this build's tag, and waits for the rollout to finish |
| 6 | Verify | Prints pods, deployment, service, the image actually running and the rollout history, then curls the Service from inside the cluster |

A `post` block adds two behaviours. On failure it dumps pod status, the deployment
description and recent container logs into the console, so a failed build can be diagnosed
from the build page. On every run it prunes dangling images so the EC2 disk does not fill
up over repeated builds.

The build stage runs in a virtualenv so that nothing is installed into the system Python,
which keeps one job from breaking another by upgrading a shared package.

---

## 3. Jenkins on AWS

Jenkins, the Docker daemon and the Minikube cluster all run on a single EC2 instance:
Ubuntu Server 24.04 LTS on `t3.large`, 2 vCPU and 8 GB RAM, with a 30 GiB gp3 root volume.

The sizing matters. A `t2.micro` cannot hold Jenkins, Docker and a Minikube node at once,
and the default 8 GiB disk fills up once a few image layers accumulate. Both failures
appear partway through a Docker build with unhelpful errors.

The security group allows inbound 22 for SSH, 8080 for the Jenkins web interface and 8081
for reaching the application, each restricted to a single source IP rather than opened to
the internet. An internet facing Jenkins on the default port is found by automated
scanners quickly, and nothing about this assignment requires public access.

Installation order on the instance:

1. Docker from the official Docker apt repository
2. OpenJDK 21 and Jenkins from the Jenkins LTS apt repository
3. kubectl and Minikube as binaries into `/usr/local/bin`
4. `python3-venv`, `python3-pip` and `git` for the build stage

### Giving Jenkins access to Docker and Kubernetes

This was the part that needed the most care, and it is worth describing because it is
where the deployment stage fails if it is done casually.

Jenkins does not run as the logged in user. It runs as a system user called `jenkins`
whose home directory is `/var/lib/jenkins`. Two consequences follow.

First, the `jenkins` user needs to be added to the `docker` group, otherwise every docker
command in the pipeline fails with a permission error on the Docker socket. Jenkins must
be restarted afterwards for the new group membership to take effect.

Second, Minikube writes its kubeconfig and client certificates into the home directory of
whichever user starts it. Started as `ubuntu`, those files land in `/home/ubuntu/.kube`
and `/home/ubuntu/.minikube`, which the `jenkins` user cannot read. The deploy stage then
fails with a connection refused against `localhost:8080`, because kubectl falls back to a
default when it cannot find a config. The cluster was therefore started as the `jenkins`
user:

```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins

sudo -u jenkins -H bash -c '
  export MINIKUBE_HOME=/var/lib/jenkins
  minikube start --driver=docker --cpus=2 --memory=2200mb
'

sudo -u jenkins -H bash -c 'kubectl get nodes'
```

The Jenkinsfile sets `KUBECONFIG` and `MINIKUBE_HOME` to match.

The pipeline job is configured as Pipeline script from SCM, pointing at the GitHub
repository on branch `main` with script path `Jenkinsfile`, so the pipeline definition is
versioned with the code rather than pasted into the Jenkins UI.

---

## 4. Pushing the image

The image is published to Docker Hub as `<YOUR DOCKERHUB USERNAME>/cca2-app`.

Authentication uses a Docker Hub personal access token with read and write scope, stored
in Jenkins as a Username with password credential under the ID `dockerhub-creds`. The
token is never present in the repository. It is injected at run time by `withCredentials`
and reaches the Docker CLI like this:

```groovy
withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                  usernameVariable: 'DH_USER',
                                  passwordVariable: 'DH_PASS')]) {
    sh '''
        echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
        docker push "$IMAGE_REF"
    '''
}
```

Two details are deliberate. The shell block uses single quotes, so Groovy does not
interpolate the secret into the script text before the shell runs, which would risk it
appearing in logs. And the login reads the token from standard input rather than taking it
as a `-p` argument, so it never appears in the process list.

Every build is tagged with the Jenkins build number, and `latest` is pushed alongside as a
convenience pointer. The reason for numbered tags is explained in section 6.

---

## 5. Deploying and accessing the application

Three manifests in `k8s/`:

- **`namespace.yaml`** creates the `cca2` namespace, so every object is scoped together
  and can be removed in one command.
- **`deployment.yaml`** runs two replicas with a rolling update strategy set to
  `maxUnavailable: 0`, so a new pod becomes Ready before an old one is removed and the
  application stays reachable throughout an update. Readiness and liveness probes use TCP
  socket checks; the liveness probe has a longer initial delay so that a slow start is
  treated as not yet ready rather than as a failure worth restarting.
- **`service.yaml`** is a NodePort Service. The selector `app: cca2-app` is what binds it
  to the pods, which is why pods can be replaced freely and keep receiving traffic. A
  LoadBalancer Service would stay Pending forever on Minikube, because there is no cloud
  provider to fulfil it.

The deploy stage applies the manifests and then pins the image:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml -n cca2
kubectl apply -f k8s/service.yaml -n cca2
kubectl set image deployment/cca2-app cca2-app="$IMAGE_REF" -n cca2 --record
kubectl rollout status deployment/cca2-app -n cca2 --timeout=180s
```

`rollout status` blocks until the new pods are Ready, so the build only reports success
once the application is genuinely serving.

### Reaching it from a browser

The NodePort is open on the Minikube node, which has an address on a Docker bridge network
internal to the EC2 instance. `minikube service --url` returns something like
`192.168.49.2:30080`, which is not reachable from outside the instance. The Service is
therefore forwarded to a port the security group allows:

```bash
kubectl port-forward --address 0.0.0.0 -n cca2 svc/cca2-app 8081:80
```

The application is then available at `http://<EC2-PUBLIC-IP>:8081`.

---

## 6. The second run

The change made for the second run was in `app/main.py`:

```python
APP_VERSION  = "v1.0"     ->  "v2.0"
RELEASE_NOTE = "Initial release"  ->  "Added pass/fail status column"
```

This string is rendered in the page banner, so the redeployment can be seen in a browser
rather than only in kubectl output. After pushing the commit, the pipeline was triggered
again and the banner changed from v1.0 to v2.0 with no manual intervention at any point.

The reason this works is worth stating, because the obvious approach fails. If every build
pushed and deployed `:latest`, the pod specification would be byte for byte identical
between runs. Kubernetes compares desired state against current state, would find no
difference, and would do nothing at all. The new image would sit in the registry and never
reach a pod. Tagging each build with `$BUILD_NUMBER` changes the pod spec, which is what
triggers a rollout, and `imagePullPolicy: Always` makes sure the node fetches the image
from the registry rather than serving a cached layer.

Evidence of the rollout:

```bash
kubectl rollout history deployment/cca2-app -n cca2
kubectl get deploy cca2-app -n cca2 \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

---

## 7. Screenshots

In `screenshots/`, numbered in the order the work was done. `docs/SCREENSHOTS.md` lists
what each one shows. The pair worth looking at together is `23-app-v1-browser.png` and
`28-app-v2-browser.png`: same URL, different version, with the pipeline run in between.

---

## 8. Known limitations

Stated plainly rather than left for the evaluator to find.

- Jenkins runs over plain HTTP. A real deployment would sit behind a reverse proxy with
  TLS.
- Builds run on the Jenkins controller rather than on separate agents. Combined with
  `jenkins` being in the `docker` group, anyone who can run a job effectively has root on
  the host.
- Minikube is a single node cluster and does not restart automatically when the EC2
  instance reboots. A systemd unit for this is described in `docs/SETUP-GUIDE.md`.
- The pipeline polls GitHub every five minutes rather than using a webhook, because the
  security group deliberately blocks inbound connections from GitHub.
- There is no image vulnerability scanning and no staging environment with an approval
  gate before deployment.

---

## 9. Running it locally without Jenkins

```bash
docker build -t cca2-app:local .
docker run --rm -p 8080:8080 cca2-app:local
# http://localhost:8080
```
