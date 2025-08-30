<?php

class Auth {
    private $db;
    
    public function __construct() {
        $this->db = Database::getInstance();
    }
    
    public function register($data) {
        $username = $data['username'];
        $email = $data['email'];
        $password = $data['password'];
        $firstName = $data['first_name'];
        $lastName = $data['last_name'];
        $role = $data['role'] ?? 'student';
        
        // Check if user already exists
        $existingUser = $this->db->fetch(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            [$username, $email]
        );
        
        if ($existingUser) {
            return ['success' => false, 'message' => 'Username or email already exists'];
        }
        
        // Hash password
        $hashedPassword = password_hash($password, PASSWORD_DEFAULT);
        
        // Insert new user
        $this->db->query(
            "INSERT INTO users (username, email, password, first_name, last_name, role) VALUES (?, ?, ?, ?, ?, ?)",
            [$username, $email, $hashedPassword, $firstName, $lastName, $role]
        );
        
        return ['success' => true, 'message' => 'Registration successful'];
    }
    
    public function login($username, $password) {
        $user = $this->db->fetch(
            "SELECT * FROM users WHERE (username = ? OR email = ?) AND is_active = 1",
            [$username, $username]
        );
        
        if (!$user || !password_verify($password, $user['password'])) {
            return ['success' => false, 'message' => 'Invalid credentials'];
        }
        
        // Set session
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['username'] = $user['username'];
        $_SESSION['role'] = $user['role'];
        $_SESSION['user_data'] = $user;
        
        return ['success' => true, 'user' => $user];
    }
    
    public function logout() {
        session_destroy();
        return ['success' => true];
    }
    
    public function isLoggedIn() {
        return isset($_SESSION['user_id']);
    }
    
    public function getCurrentUser() {
        if (!$this->isLoggedIn()) {
            return null;
        }
        
        return $this->db->fetch(
            "SELECT * FROM users WHERE id = ?",
            [$_SESSION['user_id']]
        );
    }
    
    public function hasRole($role) {
        return $this->isLoggedIn() && $_SESSION['role'] === $role;
    }
    
    public function isAdmin() {
        return $this->hasRole('admin');
    }
    
    public function isTeacher() {
        return $this->hasRole('teacher') || $this->hasRole('admin');
    }
    
    public function isStudent() {
        return $this->hasRole('student');
    }
    
    public function requireAuth() {
        if (!$this->isLoggedIn()) {
            redirect('/login.php');
        }
    }
    
    public function requireRole($role) {
        $this->requireAuth();
        if (!$this->hasRole($role)) {
            redirect('/unauthorized.php');
        }
    }
    
    public function requireAdmin() {
        $this->requireRole('admin');
    }
    
    public function requireTeacher() {
        $this->requireAuth();
        if (!$this->isTeacher()) {
            redirect('/unauthorized.php');
        }
    }
}
