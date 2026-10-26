// ============================================================================
// CCA 2 - CI/CD Pipeline
// Checkout -> Build & Test -> Docker Build -> Push -> Deploy to Minikube -> Verify
//
// EDIT THE FOUR VALUES IN THE `environment` BLOCK MARKED "EDIT ME" AND NOTHING ELSE.
// ============================================================================

pipeline {

    agent any

    environment {
        // ------------- EDIT THIS ONE LINE, NOTHING ELSE -------------
        DOCKERHUB_USER = 'your-dockerhub-username'   // your Docker Hub account name
        // ------------------------------------------------------------

        APP_NAME  = 'cca2-app'            // image name and every Kubernetes object name
        APP_PORT  = '8080'                // the port gunicorn binds inside the container
        CRED_ID   = 'dockerhub-creds'     // must match the credential ID created in Jenkins

        IMAGE      = "${DOCKERHUB_USER}/${APP_NAME}"
        IMAGE_TAG  = "${env.BUILD_NUMBER}"
        IMAGE_REF  = "${IMAGE}:${IMAGE_TAG}"
        NAMESPACE  = 'cca2'

        // Jenkins runs as the `jenkins` user, so it needs its own kubeconfig and
        // minikube state. See docs/SETUP-GUIDE.md Step 6 for why.
        KUBECONFIG    = '/var/lib/jenkins/.kube/config'
        MINIKUBE_HOME = '/var/lib/jenkins'
        PATH          = "/usr/local/bin:${env.PATH}"
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
                    echo "Commit:  $(git rev-parse --short HEAD)"
                    echo "Branch:  $(git rev-parse --abbrev-ref HEAD)"
                    echo "Message: $(git log -1 --pretty=%s)"
                '''
            }
        }

        stage('2. Build & Test') {
            steps {
                // A virtualenv keeps the build off the system Python, so one job can
                // never break another by upgrading a shared package.
                sh '''
                    set -e

                    echo "===== BUILD ====="
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --quiet --upgrade pip
                    pip install --quiet -r requirements-dev.txt
                    python --version
                    pip --version

                    echo "===== LINT ====="
                    flake8 app tests --max-line-length=120 --count

                    echo "===== UNIT AND INTEGRATION TESTS ====="
                    pytest -v --junitxml=test-results.xml
                '''
            }
            post {
                always {
                    // Publishes the pass/fail table on the Jenkins build page.
                    // Good screenshot material for the build/test criterion.
                    junit allowEmptyResults: true, testResults: 'test-results.xml'
                }
            }
        }

        stage('3. Docker Build') {
            steps {
                sh '''
                    set -e
                    docker build -t "$IMAGE_REF" -t "$IMAGE:latest" .
                    docker images | grep "$APP_NAME" | head -5
                '''
            }
        }

        stage('4. Push Image') {
            steps {
                // Single-quoted sh block on purpose: Groovy must not interpolate the
                // password into the shell script text, or it leaks into the build log.
                // This is a likely viva question.
                withCredentials([usernamePassword(
                        credentialsId: "${CRED_ID}",
                        usernameVariable: 'DH_USER',
                        passwordVariable: 'DH_PASS')]) {
                    sh '''
                        set -e
                        echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
                        docker push "$IMAGE_REF"
                        docker push "$IMAGE:latest"
                        docker logout
                    '''
                }
            }
        }

        stage('5. Deploy to Minikube') {
            steps {
                sh '''
                    set -e
                    kubectl get nodes

                    # Manifests are applied as written, then the image tag is pinned to
                    # this build. Tagging by build number (not :latest) is what makes the
                    # second run actually roll out new code.
                    kubectl apply -f k8s/namespace.yaml
                    kubectl apply -f k8s/deployment.yaml -n "$NAMESPACE"
                    kubectl apply -f k8s/service.yaml    -n "$NAMESPACE"

                    kubectl set image deployment/"$APP_NAME" \
                        "$APP_NAME"="$IMAGE_REF" -n "$NAMESPACE" --record

                    kubectl rollout status deployment/"$APP_NAME" \
                        -n "$NAMESPACE" --timeout=180s
                '''
            }
        }

        stage('6. Verify') {
            steps {
                sh '''
                    set -e
                    echo "===== PODS ====="
                    kubectl get pods -n "$NAMESPACE" -o wide

                    echo "===== DEPLOYMENT ====="
                    kubectl get deployment "$APP_NAME" -n "$NAMESPACE" -o wide

                    echo "===== SERVICE ====="
                    kubectl get svc "$APP_NAME" -n "$NAMESPACE"

                    echo "===== IMAGE ACTUALLY RUNNING ====="
                    kubectl get deployment "$APP_NAME" -n "$NAMESPACE" \
                        -o jsonpath='{.spec.template.spec.containers[0].image}'
                    echo ""

                    echo "===== ROLLOUT HISTORY ====="
                    kubectl rollout history deployment/"$APP_NAME" -n "$NAMESPACE"

                    echo "===== IN-CLUSTER SMOKE TEST ====="
                    kubectl run smoke-$BUILD_NUMBER --rm -i --restart=Never \
                        --image=curlimages/curl:latest -n "$NAMESPACE" -- \
                        curl -s -o /dev/null -w "HTTP %{http_code}\\n" \
                        "http://$APP_NAME.$NAMESPACE.svc.cluster.local" || true
                '''
            }
        }
    }

    post {
        success {
            echo "Deployed ${IMAGE_REF} to namespace ${NAMESPACE}."
            echo "Reach it with: kubectl port-forward --address 0.0.0.0 -n ${NAMESPACE} svc/${APP_NAME} 8081:80"
        }
        failure {
            sh '''
                echo "===== FAILURE DIAGNOSTICS ====="
                kubectl get pods -n "$NAMESPACE" || true
                kubectl describe deployment "$APP_NAME" -n "$NAMESPACE" || true
                kubectl logs -l app="$APP_NAME" -n "$NAMESPACE" --tail=50 --all-containers || true
            '''
        }
        always {
            sh 'docker image prune -f || true'
        }
    }
}
