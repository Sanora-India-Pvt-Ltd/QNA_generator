<?php

class Payment {
    private $db;
    
    public function __construct() {
        $this->db = Database::getInstance();
    }
    
    public function createPaymentIntent($courseId, $userId, $amount) {
        try {
            $course = $this->db->fetch("SELECT * FROM courses WHERE id = ?", [$courseId]);
            if (!$course) {
                return ['success' => false, 'message' => 'Course not found'];
            }
            
            // Create payment record
            $this->db->query(
                "INSERT INTO payments (student_id, course_id, amount, currency, status) VALUES (?, ?, ?, 'USD', 'pending')",
                [$userId, $courseId, $amount]
            );
            
            $paymentId = $this->db->lastInsertId();
            
            // For demo purposes, create a mock payment intent
            $paymentIntentId = 'pi_' . uniqid();
            
            // Update payment record with mock payment intent ID
            $this->db->query(
                "UPDATE payments SET stripe_payment_intent_id = ? WHERE id = ?",
                [$paymentIntentId, $paymentId]
            );
            
            return [
                'success' => true,
                'payment_intent_id' => $paymentIntentId,
                'client_secret' => 'mock_client_secret_' . uniqid(),
                'payment_id' => $paymentId
            ];
            
        } catch (Exception $e) {
            return ['success' => false, 'message' => $e->getMessage()];
        }
    }
    
    public function confirmPayment($paymentIntentId) {
        try {
            // For demo purposes, simulate payment confirmation
            $payment = $this->db->fetch(
                "SELECT * FROM payments WHERE stripe_payment_intent_id = ?",
                [$paymentIntentId]
            );
            
            if ($payment) {
                // Update payment status
                $this->db->query(
                    "UPDATE payments SET status = 'completed' WHERE stripe_payment_intent_id = ?",
                    [$paymentIntentId]
                );
                
                // Enroll student in course
                $this->db->query(
                    "INSERT INTO enrollments (student_id, course_id) VALUES (?, ?) ON DUPLICATE KEY UPDATE enrolled_at = NOW()",
                    [$payment['student_id'], $payment['course_id']]
                );
                
                return ['success' => true, 'message' => 'Payment confirmed successfully'];
            } else {
                return ['success' => false, 'message' => 'Payment not found'];
            }
            
        } catch (Exception $e) {
            return ['success' => false, 'message' => $e->getMessage()];
        }
    }
    
    public function getPaymentById($paymentId) {
        return $this->db->fetch(
            "SELECT p.*, c.title as course_title, u.first_name, u.last_name 
             FROM payments p 
             JOIN courses c ON p.course_id = c.id 
             JOIN users u ON p.student_id = u.id 
             WHERE p.id = ?",
            [$paymentId]
        );
    }
    
    public function getPaymentsByUser($userId) {
        return $this->db->fetchAll(
            "SELECT p.*, c.title as course_title 
             FROM payments p 
             JOIN courses c ON p.course_id = c.id 
             WHERE p.student_id = ? 
             ORDER BY p.created_at DESC",
            [$userId]
        );
    }
    
    public function getAllPayments($limit = null, $offset = 0) {
        $sql = "SELECT p.*, c.title as course_title, u.first_name, u.last_name 
                FROM payments p 
                JOIN courses c ON p.course_id = c.id 
                JOIN users u ON p.student_id = u.id 
                ORDER BY p.created_at DESC";
        
        if ($limit) {
            $sql .= " LIMIT ? OFFSET ?";
            return $this->db->fetchAll($sql, [$limit, $offset]);
        }
        
        return $this->db->fetchAll($sql);
    }
    
    public function getPaymentStats() {
        $stats = [];
        
        // Total revenue
        $stats['total_revenue'] = $this->db->fetch(
            "SELECT SUM(amount) as total FROM payments WHERE status = 'completed'"
        )['total'] ?? 0;
        
        // Monthly revenue
        $stats['monthly_revenue'] = $this->db->fetch(
            "SELECT SUM(amount) as total FROM payments WHERE status = 'completed' AND MONTH(created_at) = MONTH(NOW()) AND YEAR(created_at) = YEAR(NOW())"
        )['total'] ?? 0;
        
        // Total payments
        $stats['total_payments'] = $this->db->fetch(
            "SELECT COUNT(*) as count FROM payments WHERE status = 'completed'"
        )['count'] ?? 0;
        
        // Pending payments
        $stats['pending_payments'] = $this->db->fetch(
            "SELECT COUNT(*) as count FROM payments WHERE status = 'pending'"
        )['count'] ?? 0;
        
        return $stats;
    }
    
    public function refundPayment($paymentId) {
        try {
            $payment = $this->getPaymentById($paymentId);
            if (!$payment || $payment['status'] !== 'completed') {
                return ['success' => false, 'message' => 'Payment not found or not completed'];
            }
            
            // For demo purposes, simulate refund
            // Update payment status
            $this->db->query(
                "UPDATE payments SET status = 'refunded' WHERE id = ?",
                [$paymentId]
            );
            
            // Remove enrollment
            $this->db->query(
                "DELETE FROM enrollments WHERE student_id = ? AND course_id = ?",
                [$payment['student_id'], $payment['course_id']]
            );
            
            return ['success' => true, 'message' => 'Payment refunded successfully'];
            
        } catch (Exception $e) {
            return ['success' => false, 'message' => $e->getMessage()];
        }
    }
    
    public function processWebhook($payload, $sigHeader) {
        try {
            // For demo purposes, simulate webhook processing
            $data = json_decode($payload, true);
            
            if (isset($data['type'])) {
                switch ($data['type']) {
                    case 'payment_intent.succeeded':
                        if (isset($data['data']['object']['id'])) {
                            $this->confirmPayment($data['data']['object']['id']);
                        }
                        break;
                        
                    case 'payment_intent.payment_failed':
                        if (isset($data['data']['object']['id'])) {
                            $this->db->query(
                                "UPDATE payments SET status = 'failed' WHERE stripe_payment_intent_id = ?",
                                [$data['data']['object']['id']]
                            );
                        }
                        break;
                }
            }
            
            return ['success' => true];
            
        } catch (Exception $e) {
            return ['success' => false, 'message' => $e->getMessage()];
        }
    }
    
    public function getStripePublicKey() {
        return $_ENV['STRIPE_PUBLISHABLE_KEY'] ?? 'pk_test_mock_key';
    }
}

