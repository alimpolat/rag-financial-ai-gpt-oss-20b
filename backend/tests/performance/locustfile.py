"""Performance tests for RAG Financial AI system using Locust."""

import json
import random
import time
from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGFinancialAIUser(HttpUser):
    """Simulates a user interacting with the RAG Financial AI system."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a simulated user starts."""
        # Attempt to login
        self.login()
        
        # Load sample questions for chat testing
        self.sample_questions = [
            "What was the revenue last quarter?",
            "Show me the expense breakdown",
            "What is our profit margin?",
            "Compare Q1 to Q2 performance",
            "What are the key financial metrics?",
            "Show me the cash flow statement",
            "What is the debt to equity ratio?",
            "Analyze the revenue trends",
            "What are our operating expenses?",
            "Show me the balance sheet summary"
        ]
        
        # Track session for realistic behavior
        self.chat_session_id = f"perf-test-{self.environment.runner.user_count}-{int(time.time())}"
        self.message_count = 0
    
    def login(self):
        """Authenticate and get access token."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123"
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.client.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
            response.success()
        else:
            response.failure(f"Login failed: {response.text}")
            raise RescheduleTask()
    
    @task(3)
    def send_chat_message(self):
        """Send a chat message and wait for response."""
        question = random.choice(self.sample_questions)
        self.message_count += 1
        
        with self.client.post(
            "/api/v1/chat",
            json={
                "message": question,
                "session_id": self.chat_session_id,
                "include_sources": True
            },
            catch_response=True,
            name="/api/v1/chat"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                if "response" in data and "sources" in data:
                    # Check response time
                    if response.elapsed.total_seconds() > 5:
                        response.failure(f"Response too slow: {response.elapsed.total_seconds()}s")
                    else:
                        response.success()
                        
                        # Log confidence for monitoring
                        confidence = data.get("confidence", 0)
                        if confidence < 0.5:
                            logger.warning(f"Low confidence response: {confidence}")
                else:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"Chat failed: {response.text}")
    
    @task(1)
    def get_chat_history(self):
        """Retrieve chat history."""
        with self.client.get(
            f"/api/v1/chat/history?session_id={self.chat_session_id}",
            catch_response=True,
            name="/api/v1/chat/history"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "messages" in data:
                    response.success()
                else:
                    response.failure("Invalid history structure")
            else:
                response.failure(f"History fetch failed: {response.text}")
    
    @task(2)
    def list_documents(self):
        """List available documents."""
        with self.client.get(
            "/api/v1/documents",
            catch_response=True,
            name="/api/v1/documents"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "documents" in data:
                    response.success()
                else:
                    response.failure("Invalid documents structure")
            else:
                response.failure(f"Document list failed: {response.text}")
    
    @task(1)
    def upload_document(self):
        """Upload a test document."""
        # Create a small test PDF
        test_content = b"%PDF-1.4\nTest financial document for performance testing"
        
        files = {
            'file': ('test_financial_doc.pdf', test_content, 'application/pdf')
        }
        
        with self.client.post(
            "/api/v1/documents/upload",
            files=files,
            catch_response=True,
            name="/api/v1/documents/upload"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "document_id" in data:
                    response.success()
                    # Store document ID for potential deletion
                    self.uploaded_doc_id = data["document_id"]
                else:
                    response.failure("Upload succeeded but no document_id returned")
            else:
                response.failure(f"Upload failed: {response.text}")
    
    @task(1)
    def health_check(self):
        """Check system health."""
        with self.client.get(
            "/api/v1/health",
            catch_response=True,
            name="/api/v1/health"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure(f"System unhealthy: {data}")
            else:
                response.failure(f"Health check failed: {response.text}")
    
    def on_stop(self):
        """Called when a simulated user stops."""
        # Optionally logout
        try:
            self.client.post("/api/v1/auth/logout")
        except:
            pass


class AdminUser(HttpUser):
    """Simulates an admin user performing administrative tasks."""
    
    wait_time = between(2, 5)
    weight = 1  # Lower weight than regular users
    
    def on_start(self):
        """Admin login."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "admin123"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.client.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
    
    @task(2)
    def view_analytics(self):
        """View system analytics."""
        with self.client.get(
            "/api/v1/admin/analytics",
            catch_response=True,
            name="/api/v1/admin/analytics"
        ) as response:
            if response.status_code in [200, 404]:  # 404 if endpoint not implemented
                response.success()
            else:
                response.failure(f"Analytics failed: {response.text}")
    
    @task(1)
    def manage_users(self):
        """List and manage users."""
        with self.client.get(
            "/api/v1/admin/users",
            catch_response=True,
            name="/api/v1/admin/users"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"User management failed: {response.text}")
    
    @task(1)
    def system_metrics(self):
        """Check system metrics."""
        with self.client.get(
            "/api/v1/admin/metrics",
            catch_response=True,
            name="/api/v1/admin/metrics"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Metrics failed: {response.text}")


class MixedLoadTest(HttpUser):
    """Mixed load test simulating different user behaviors."""
    
    tasks = {RAGFinancialAIUser: 9, AdminUser: 1}  # 90% regular users, 10% admin


# Event handlers for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    logger.info("Performance test starting...")
    logger.info(f"Target host: {environment.host}")
    logger.info(f"Total users: {environment.parsed_options.num_users}")
    logger.info(f"Spawn rate: {environment.parsed_options.spawn_rate}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    logger.info("Performance test completed!")
    
    # Log summary statistics
    stats = environment.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Failed requests: {stats.total.num_failures}")
    logger.info(f"Median response time: {stats.total.median_response_time}ms")
    logger.info(f"95th percentile: {stats.total.get_response_time_percentile(0.95)}ms")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Called after each request."""
    if exception:
        logger.error(f"Request failed: {name} - {exception}")
    elif response_time > 3000:  # Log slow requests (>3s)
        logger.warning(f"Slow request: {name} - {response_time}ms")


# Custom test scenarios
class StressTestUser(HttpUser):
    """Stress test with rapid requests."""
    
    wait_time = between(0.1, 0.5)  # Very short wait times
    
    def on_start(self):
        """Quick login."""
        self.client.post(
            "/api/v1/auth/login",
            json={"email": "stress@test.com", "password": "test123"}
        )
    
    @task
    def rapid_chat(self):
        """Send rapid chat messages."""
        self.client.post(
            "/api/v1/chat",
            json={
                "message": "Quick test message",
                "session_id": f"stress-{time.time()}"
            },
            catch_response=True
        )


class SpikeTestUser(HttpUser):
    """Spike test simulating sudden traffic increase."""
    
    wait_time = between(0.5, 1)
    
    @task
    def spike_request(self):
        """Simple request for spike testing."""
        self.client.get("/api/v1/health")
        self.client.get("/api/v1/documents")


# Configuration for different test scenarios
"""
Usage examples:

1. Normal load test (50 users over 2 minutes):
   locust -f locustfile.py --host http://localhost:8000 --users 50 --spawn-rate 5 --run-time 2m

2. Stress test (200 users quickly):
   locust -f locustfile.py --host http://localhost:8000 --users 200 --spawn-rate 20 --run-time 5m

3. Spike test (sudden 100 users):
   locust -f locustfile.py --host http://localhost:8000 --users 100 --spawn-rate 100 --run-time 1m

4. Endurance test (steady load for 30 minutes):
   locust -f locustfile.py --host http://localhost:8000 --users 30 --spawn-rate 2 --run-time 30m

5. Web UI mode:
   locust -f locustfile.py --host http://localhost:8000
   Then open http://localhost:8089
"""