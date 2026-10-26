
pipeline {
    agent any

    environment {
        DOCKERHUB_USER = 'vaibhaviz'
        APP_NAME       = 'cca2-app'
        APP_PORT       = '8080'
        CRED_ID        = 'dockerhub-creds'
        NAMESPACE      = 'cca2'

        IMAGE          = "${DOCKERHUB_USER}/${APP_NAME}"
        IMAGE_TAG      = "${BUILD_NUMBER}"
        IMAGE_REF      = "${IMAGE}:${IMAGE_TAG}"

        KUBECONFIG     = '/var/lib/jenkins/.kube/config'
        MINIKUBE_HOME  = '/var/lib/jenkins'
        PATH           = "/usr/local/bin:${env.PATH}"
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '15'))
        timeout(time: 25, unit: 'MINUTES')
    }

    stages {
        stage('1. Checkout') {
            steps {
                checkout scm
                sh '''
                    set -e
                    echo "Commit: $(git rev-parse --short HEAD)"
                    echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
                '''
            }
        }

        stage('2. Build and Test') {
            steps {
                sh '''
                    set -e
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --quiet --upgrade pip
                    pip install --quiet -r requirements-dev.txt

                    flake8 app tests --max-line-length=120 --count
                    python -m pytest -v --junitxml=test-results.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true,
                          testResults: 'test-results.xml'
                }
            }
        }

        stage('3. Docker Build') {
            steps {
                sh '''
                    set -e
                    docker build -t "$IMAGE_REF" .
                    docker image inspect "$IMAGE_REF" >/dev/null
                '''
            }
        }

        stage('4. Push Image') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: "${CRED_ID}",
                        usernameVariable: 'DH_USER',
                        passwordVariable: 'DH_PASS'
                    )
                ]) {
                    sh '''
                        set -eu
                        echo "$DH_PASS" |
                            docker login -u "$DH_USER" --password-stdin
                        docker push "$IMAGE_REF"
                        docker logout
                    '''
                }
            }
        }

        stage('5. Deploy to Minikube') {
            steps {
                sh '''
                    set -eu

                    echo "Checking Kubernetes connection..."
                    kubectl get nodes

                    kubectl apply -f k8s/namespace.yaml
                    kubectl apply -f k8s/service.yaml
                    kubectl apply -f k8s/deployment.yaml

                    echo "Deploying image: $IMAGE_REF"

                    kubectl set image \
                        deployment/"$APP_NAME" \
                        "$APP_NAME"="$IMAGE_REF" \
                        -n "$NAMESPACE"

                    kubectl rollout status \
                        deployment/"$APP_NAME" \
                        -n "$NAMESPACE" \
                        --timeout=180s
                '''
            }
        }

        stage('6. Verify') {
            steps {
                sh '''
                    set -eu

                    echo "===== PODS ====="
                    kubectl get pods -n "$NAMESPACE" -o wide

                    echo "===== DEPLOYMENT ====="
                    kubectl get deployment "$APP_NAME" -n "$NAMESPACE"

                    echo "===== SERVICE ====="
                    kubectl get svc "$APP_NAME" -n "$NAMESPACE"

                    echo "===== DEPLOYED IMAGE ====="
                    kubectl get deployment "$APP_NAME" -n "$NAMESPACE" \
                      -o jsonpath='{.spec.template.spec.containers[0].image}'
                    echo

                    echo "===== ROLLOUT HISTORY ====="
                    kubectl rollout history \
                      deployment/"$APP_NAME" -n "$NAMESPACE"

                    echo "===== SMOKE TEST ====="
                    kubectl run "smoke-$BUILD_NUMBER" \
                      --rm -i --restart=Never \
                      --image=curlimages/curl:latest \
                      -n "$NAMESPACE" -- \
                      curl --fail --silent --show-error \
                      --max-time 10 \
                      "http://$APP_NAME.$NAMESPACE.svc.cluster.local/" 
                '''
            }
        }
    }

    post {
        success {
            echo "Successfully deployed ${IMAGE_REF} to ${NAMESPACE}."
            echo "NodePort: 30080"
        }

        failure {
            echo "Pipeline failed. Collecting Kubernetes diagnostics."

            sh '''
                kubectl get nodes || true
                kubectl get pods -n "$NAMESPACE" -o wide || true
                kubectl describe deployment "$APP_NAME" \
                    -n "$NAMESPACE" || true
                kubectl logs -l app="$APP_NAME" \
                    -n "$NAMESPACE" --tail=50 \
                    --all-containers=true || true
            '''
        }

        always {
            sh 'docker image prune -f || true'
        }
    }
}
