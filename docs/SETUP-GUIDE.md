# Setup Guide

Everything needed to take this repository from nothing to a green pipeline with the app
running on Minikube. Follow it in order. Do not skip Step 6, which is where most people
lose a day.

This guide is for you, not for submission.

---

## 0. What you are building

```
       your laptop
            |
            |  git push
            v
      GitHub repository
            |
            |  Jenkins polls / you click Build Now
            v
  ======  ONE AWS EC2 INSTANCE  ===========================
  |                                                       |
  |   Jenkins  ---->  Docker build  ---->  docker push ------>  Docker Hub
  |      |                                                |         |
  |      |  kubectl apply + set image                     |         |
  |      v                                                |         |
  |   Minikube cluster  <------------- image pull --------|---------+
  |      - Deployment (2 pods)                            |
  |      - Service (NodePort 30080)                       |
  =========================================================
```

Jenkins, Docker and Minikube all run on the same EC2 instance. The image makes a round
trip out to Docker Hub and back, which is the point: Kubernetes pulls from a registry,
not from the local Docker daemon.

---

## 1. Accounts you need

| Account | Cost | Notes |
|---|---|---|
| GitHub | free | public repo is fine and makes the evaluator's life easier |
| Docker Hub | free | you need a **Personal Access Token**, not your password |
| AWS | **not free tier for this** | see the sizing warning in Step 3 |

### Docker Hub access token

Docker Hub → your avatar → **Account Settings** → **Personal access tokens** →
**Generate new token**. Scope: **Read & Write**. Copy it immediately, it is shown once.

You will paste this into Jenkins in Step 8. Never put it in a file in the repo.

---

## 2. Push this project to GitHub

On your laptop, inside the unzipped folder:

```bash
git init
git add .
git commit -m "Student Grade Management System with CI/CD pipeline"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

Before you push, edit two values:

1. `Jenkinsfile` line with `DOCKERHUB_USER` → your Docker Hub username
2. `k8s/deployment.yaml` → the `image:` line → `<your-dockerhub-username>/cca2-app:latest`

Check it runs locally first:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q          # expect 57 passed
python -m app.main # then open http://localhost:8080
```

---

## 3. Launch the EC2 instance

**Sizing warning.** Jenkins, the Docker daemon and a Minikube node on one box will not
fit in `t2.micro`. It will appear to work and then die partway through a Docker build.
Use **t3.large** (2 vCPU, 8 GB). `t3.medium` (4 GB) can work but leaves no headroom.

This is **outside the free tier**. Check current on-demand pricing for your region before
launching, and **stop the instance whenever you are not working on it**. Stopping keeps
the disk and stops the hourly charge. Terminating deletes everything.

EC2 → Launch instance:

| Setting | Value |
|---|---|
| Name | `cca2-jenkins` |
| AMI | Ubuntu Server 24.04 LTS |
| Instance type | `t3.large` |
| Key pair | create one, download the `.pem`, keep it safe |
| Storage | **30 GiB gp3** (the 8 GiB default fills up and the build fails) |

**Security group** — create new, with these inbound rules:

| Type | Port | Source | Why |
|---|---|---|---|
| SSH | 22 | **My IP** | your terminal |
| Custom TCP | 8080 | **My IP** | Jenkins web UI |
| Custom TCP | 8081 | **My IP** | the app, via port-forward in Step 10 |

Use **My IP**, not `0.0.0.0/0`. An open Jenkins on the public internet gets found by
bots within hours, and "why did you restrict the source?" is a fair viva question with a
good answer.

Connect:

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
```

---

## 4. Install Docker

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin

sudo usermod -aG docker ubuntu
newgrp docker          # or log out and back in

docker run --rm hello-world
```

---

## 5. Install Jenkins

```bash
sudo apt install -y fontconfig openjdk-21-jre-headless

sudo wget -O /etc/apt/keyrings/jenkins-keyring.asc \
  https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key

echo "deb [signed-by=/etc/apt/keyrings/jenkins-keyring.asc] \
https://pkg.jenkins.io/debian-stable binary/" \
  | sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null

sudo apt update
sudo apt install -y jenkins

sudo systemctl enable --now jenkins
sudo systemctl status jenkins --no-pager
```

> The signing key moved to `jenkins.io-2026.key` in early 2026. Most tutorials online still
> point at `jenkins.io-2023.key`, which now fails with a `NO_PUBKEY` error. If you hit that,
> you used an old guide.

Also install the Python build tooling Jenkins will need:

```bash
sudo apt install -y python3-venv python3-pip git
```

---

## 6. Install Minikube and kubectl, and give Jenkins access

**This is the step that breaks everything if you rush it.**

Jenkins does not run as you. It runs as a system user called `jenkins` whose home is
`/var/lib/jenkins`. If you start Minikube as `ubuntu`, the cluster credentials land in
`/home/ubuntu/.kube/` and `/home/ubuntu/.minikube/`, which the `jenkins` user cannot read.
Your pipeline then fails at the deploy stage with a connection-refused or permission error.

The clean fix is to run Minikube **as the jenkins user** from the start.

Install the binaries:

```bash
# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
rm kubectl
kubectl version --client

# minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
rm minikube-linux-amd64
minikube version
```

Let the `jenkins` user drive Docker, then restart Jenkins so it picks up the new group:

```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
sleep 20
```

Start the cluster **as jenkins**:

```bash
sudo -u jenkins -H bash -c '
  export MINIKUBE_HOME=/var/lib/jenkins
  minikube start --driver=docker --cpus=2 --memory=2200mb
'
```

Verify that the jenkins user, specifically, can reach the cluster:

```bash
sudo -u jenkins -H bash -c 'kubectl get nodes'
```

You must see a node in `Ready` state. If this command fails, **stop and fix it here**.
Nothing downstream will work until it passes.

### Surviving a reboot

Minikube does not come back by itself when the instance restarts. If you stop and start
the EC2 instance, run this before building:

```bash
sudo -u jenkins -H bash -c 'export MINIKUBE_HOME=/var/lib/jenkins; minikube start --driver=docker'
```

To automate it, create `/etc/systemd/system/minikube.service`:

```ini
[Unit]
Description=Minikube for Jenkins
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=jenkins
Environment=MINIKUBE_HOME=/var/lib/jenkins
Environment=HOME=/var/lib/jenkins
ExecStart=/usr/local/bin/minikube start --driver=docker --cpus=2 --memory=2200mb
ExecStop=/usr/local/bin/minikube stop

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable minikube
```

---

## 7. Unlock Jenkins and install plugins

Open `http://<EC2-PUBLIC-IP>:8080` in a browser.

Get the initial password:

```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

Then:

1. Paste the password
2. Choose **Install suggested plugins** (this gives you Pipeline, Git, Credentials Binding and JUnit)
3. Create your admin user. Write the username and password down.
4. Accept the default Jenkins URL

Then **Manage Jenkins → Plugins → Available plugins** and install:

| Plugin | What it is for here |
|---|---|
| Docker Pipeline | not strictly required, since this pipeline calls `docker` through `sh`, but evaluators look for it and it costs nothing |
| Kubernetes CLI | optional, provides `withKubeConfig` if you later want credential-scoped kubeconfig |

Restart Jenkins when prompted.

> Being able to say *"I drive Docker through shell steps rather than the Docker Pipeline
> DSL, so the plugin is installed but not load-bearing"* is a stronger viva answer than
> listing plugins you cannot explain.

---

## 8. Add the Docker Hub credential

**Manage Jenkins → Credentials → System → Global credentials → Add Credentials**

| Field | Value |
|---|---|
| Kind | Username with password |
| Username | your Docker Hub username |
| Password | the **access token** from Step 1 |
| ID | `dockerhub-creds` |
| Description | Docker Hub push token |

The ID must be exactly `dockerhub-creds`, because the Jenkinsfile refers to it by that
name. If you call it something else, change `CRED_ID` in the Jenkinsfile to match.

---

## 9. Create the pipeline job

**New Item** → name it `cca2-pipeline` → **Pipeline** → OK.

Scroll to **Pipeline**:

| Field | Value |
|---|---|
| Definition | Pipeline script from SCM |
| SCM | Git |
| Repository URL | `https://github.com/<you>/<repo>.git` |
| Credentials | none, if the repo is public |
| Branch Specifier | `*/main` |
| Script Path | `Jenkinsfile` |

Optional but worth a sentence in the viva: tick **Poll SCM** with schedule `H/5 * * * *`
so Jenkins checks GitHub every five minutes. A webhook would be better, but a webhook
needs GitHub to reach your EC2 instance, which your security group deliberately blocks.

**Save**, then **Build Now**.

---

## 10. Watch it run, then open the app

The first run takes a few minutes because it pulls the Python base image. Watch
**Console Output**. All six stages should go green.

The app is inside the cluster, on a network the internet cannot see. Expose it:

```bash
sudo -u jenkins -H bash -c \
  'kubectl port-forward --address 0.0.0.0 -n cca2 svc/cca2-app 8081:80' &
```

Now open `http://<EC2-PUBLIC-IP>:8081` in your browser. You should see the grade table
with a **v1.0** chip in the banner.

> `minikube service --url` gives you a `192.168.49.x` address. That is internal to the
> EC2 instance and will not open from your laptop. Use the port-forward above instead.
> Knowing why is a good viva answer.

Check it by hand too:

```bash
sudo -u jenkins -H bash -c 'kubectl get all -n cca2'
sudo -u jenkins -H bash -c 'kubectl get pods -n cca2 -o wide'
curl -s localhost:8081/health
```

---

## 11. The code change and second run

This is mandatory requirement 9 and it is worth real marks. On your laptop, edit
`app/main.py`:

```python
APP_VERSION  = "v2.0"
RELEASE_NOTE = "Added pass/fail status column"
```

Then:

```bash
git add app/main.py
git commit -m "Release v2.0: update version banner"
git push
```

In Jenkins, **Build Now** again (or wait for the poll). Watch the deploy stage. Then:

- refresh `http://<EC2-PUBLIC-IP>:8081` and the chip reads **v2.0**
- `kubectl rollout history deployment/cca2-app -n cca2` shows two revisions
- `kubectl get pods -n cca2` shows pods with fresh ages

The reason this works is in the Jenkinsfile: every build tags the image with
`$BUILD_NUMBER` rather than reusing `:latest`, and the Deployment sets
`imagePullPolicy: Always`. If you tagged everything `:latest`, Kubernetes would see no
change to the pod spec and would not restart anything. Your "new" version would never
appear. **This is the single most common way this assignment fails, and a very likely
viva question.**

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `NO_PUBKEY` adding the Jenkins repo | old 2023 key from an outdated tutorial | use `jenkins.io-2026.key` as in Step 5 |
| `permission denied ... docker.sock` in the build | `jenkins` not in the `docker` group, or Jenkins not restarted after | `sudo usermod -aG docker jenkins && sudo systemctl restart jenkins` |
| `The connection to the server localhost:8080 was refused` at deploy | Jenkins cannot find a kubeconfig | you started Minikube as `ubuntu`, not `jenkins`. Redo Step 6. |
| `ImagePullBackOff` | wrong username in the image name, or the push stage silently failed | `kubectl describe pod -n cca2 <pod>` and read the events |
| `ErrImagePull` on a private repo | the repo on Docker Hub defaulted to private | make it public, or add an `imagePullSecret` |
| Pods stuck `Pending` | Minikube has no room | `minikube delete` then start again with more memory, or resize the instance |
| Build dies around `docker build`, no clear error | out of RAM or disk | `free -h` and `df -h`. This is the `t2.micro` / 8 GiB disk trap. |
| Second run deploys but the page still shows v1.0 | browser cache | hard refresh, then check `kubectl get deploy cca2-app -n cca2 -o jsonpath='{.spec.template.spec.containers[0].image}'` |
| Everything broke after a reboot | Minikube does not auto-start | see "Surviving a reboot" in Step 6 |

Useful diagnostics:

```bash
sudo -u jenkins -H bash -c 'kubectl describe deployment cca2-app -n cca2'
sudo -u jenkins -H bash -c 'kubectl logs -l app=cca2-app -n cca2 --tail=100'
sudo journalctl -u jenkins -n 100 --no-pager
```

---

## Before the demo

- [ ] Instance started, and Minikube started after it
- [ ] `kubectl get nodes` as jenkins shows `Ready`
- [ ] Port-forward running, app opens in a browser
- [ ] Jenkins shows at least two successful builds
- [ ] Docker Hub shows at least two image tags
- [ ] You have read `VIVA-PREP.md` and can answer the starred questions
