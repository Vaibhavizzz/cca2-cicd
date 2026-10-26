# Screenshot Checklist

Screenshots are a listed submittable. Capture them as you go, not at the end, because
some of them only exist for a moment.

Save them into a `screenshots/` folder in the repo using the numbered filenames below, so
the evaluator can follow them in order. Every shot maps to a rubric line.

Crop to the relevant window. A full 4K desktop screenshot where the terminal text is
unreadable scores nothing.

---

## Project and GitHub, 1 mark

| # | Filename | What to capture |
|---|---|---|
| 01 | `01-github-repo.png` | Repository landing page, file tree visible, showing `app/`, `tests/`, `k8s/`, `Dockerfile`, `Jenkinsfile` |
| 02 | `02-local-tests.png` | Terminal on your laptop running `pytest -q` with 57 passed |

---

## AWS and Jenkins, 1.5 marks

| # | Filename | What to capture |
|---|---|---|
| 03 | `03-ec2-instance.png` | EC2 console, instance Running, with instance type and public IP visible |
| 04 | `04-security-group.png` | Inbound rules showing 22, 8080 and 8081 scoped to your IP |
| 05 | `05-jenkins-dashboard.png` | Jenkins dashboard in a browser, URL bar showing the EC2 public IP on 8080 |
| 06 | `06-jenkins-plugins.png` | Manage Jenkins → Plugins → Installed, with Pipeline, Git and Docker Pipeline visible |
| 07 | `07-jenkins-credentials.png` | Credentials list showing `dockerhub-creds`. The secret is hidden, which is the point. |
| 08 | `08-pipeline-job-config.png` | Job config showing Pipeline script from SCM, your repo URL, branch `*/main`, script path `Jenkinsfile` |
| 09 | `09-minikube-as-jenkins.png` | Terminal: `sudo -u jenkins -H bash -c 'kubectl get nodes'` returning a Ready node |

---

## Dockerfile and image build, 1.5 marks

| # | Filename | What to capture |
|---|---|---|
| 10 | `10-dockerfile.png` | The Dockerfile open in an editor or `cat Dockerfile` |
| 11 | `11-docker-build-log.png` | Jenkins console output across the Docker Build stage, ending in a successful build |
| 12 | `12-docker-images.png` | Terminal `docker images` showing your image with the build-number tag |

---

## Jenkinsfile and automated pipeline, 2 marks

| # | Filename | What to capture |
|---|---|---|
| 13 | `13-jenkinsfile.png` | The Jenkinsfile open, stage names visible |
| 14 | `14-stage-view-run1.png` | Jenkins Stage View, build #1, all six stages green with timings |
| 15 | `15-test-results.png` | The JUnit test result page on the build, showing 57 tests and zero failures |
| 16 | `16-console-full-run1.png` | Console output of run #1 ending in `Finished: SUCCESS` |

---

## Registry integration, 1 mark

| # | Filename | What to capture |
|---|---|---|
| 17 | `17-push-log.png` | Console output of the Push Image stage showing the digest and that the token is masked |
| 18 | `18-dockerhub-tags.png` | Docker Hub repository Tags page, with at least two numbered tags plus `latest` |

---

## Kubernetes on Minikube, 1.5 marks

| # | Filename | What to capture |
|---|---|---|
| 19 | `19-k8s-manifests.png` | `k8s/deployment.yaml` and `k8s/service.yaml` open |
| 20 | `20-kubectl-get-all.png` | `kubectl get all -n cca2` showing pods, deployment, replicaset and service |
| 21 | `21-pods-wide.png` | `kubectl get pods -n cca2 -o wide` with both pods Running and 1/1 Ready |
| 22 | `22-describe-deployment.png` | `kubectl describe deployment cca2-app -n cca2`, image name with the build tag visible |

---

## Verification and the code change, 1.5 marks

| # | Filename | What to capture |
|---|---|---|
| 23 | `23-app-v1-browser.png` | The app in a browser showing the **v1.0** chip, EC2 public IP in the URL bar |
| 24 | `24-code-change-diff.png` | The GitHub commit diff, or `git diff`, showing v1.0 changed to v2.0 |
| 25 | `25-stage-view-run2.png` | Stage View for build #2, all green |
| 26 | `26-rollout-history.png` | `kubectl rollout history deployment/cca2-app -n cca2` showing two revisions |
| 27 | `27-new-pods.png` | `kubectl get pods -n cca2` after the second run, pods with fresh ages |
| 28 | `28-app-v2-browser.png` | The app in a browser showing the **v2.0** chip |
| 29 | `29-image-in-use.png` | `kubectl get deploy cca2-app -n cca2 -o jsonpath='{.spec.template.spec.containers[0].image}'` showing tag 2 |

---

## Pair them

Shots 23 and 28 are the single most persuasive pair in the submission, because together
they prove the pipeline actually delivered new code rather than just turning green. Make
sure both show the same URL and differ only in the version chip. Put them side by side in
the report if you can.

---

## Before you submit

- [ ] 29 files in `screenshots/`
- [ ] Every terminal screenshot is legible at 100% zoom
- [ ] No access token, password or private key visible in any shot
- [ ] Your name or roll number appears somewhere, such as the shell prompt or the GitHub account
- [ ] `screenshots/` is committed and pushed
