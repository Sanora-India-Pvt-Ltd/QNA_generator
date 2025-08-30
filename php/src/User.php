<?php

class User {
    private $db;
    
    public function __construct() {
        $this->db = Database::getInstance();
    }
    
    public function getAll($role = null, $limit = null, $offset = 0) {
        $sql = "SELECT * FROM users";
        $params = [];
        
        if ($role) {
            $sql .= " WHERE role = ?";
            $params[] = $role;
        }
        
        $sql .= " ORDER BY created_at DESC";
        
        if ($limit) {
            $sql .= " LIMIT ? OFFSET ?";
            $params[] = $limit;
            $params[] = $offset;
        }
        
        return $this->db->fetchAll($sql, $params);
    }
    
    public function getById($id) {
        return $this->db->fetch("SELECT * FROM users WHERE id = ?", [$id]);
    }
    
    public function getByUsername($username) {
        return $this->db->fetch("SELECT * FROM users WHERE username = ?", [$username]);
    }
    
    public function getByEmail($email) {
        return $this->db->fetch("SELECT * FROM users WHERE email = ?", [$email]);
    }
    
    public function create($data) {
        $hashedPassword = password_hash($data['password'], PASSWORD_DEFAULT);
        
        $this->db->query(
            "INSERT INTO users (username, email, password, first_name, last_name, role, bio) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                $data['username'],
                $data['email'],
                $hashedPassword,
                $data['first_name'],
                $data['last_name'],
                $data['role'] ?? 'student',
                $data['bio'] ?? null
            ]
        );
        
        return $this->db->lastInsertId();
    }
    
    public function update($id, $data) {
        $updateFields = [];
        $params = [];
        
        $fields = ['username', 'email', 'first_name', 'last_name', 'role', 'bio', 'is_active'];
        
        foreach ($fields as $field) {
            if (isset($data[$field])) {
                $updateFields[] = "$field = ?";
                $params[] = $data[$field];
            }
        }
        
        if (isset($data['password']) && !empty($data['password'])) {
            $updateFields[] = "password = ?";
            $params[] = password_hash($data['password'], PASSWORD_DEFAULT);
        }
        
        if (empty($updateFields)) {
            return false;
        }
        
        $params[] = $id;
        
        $sql = "UPDATE users SET " . implode(', ', $updateFields) . " WHERE id = ?";
        $this->db->query($sql, $params);
        
        return true;
    }
    
    public function delete($id) {
        return $this->db->query("DELETE FROM users WHERE id = ?", [$id]);
    }
    
    public function getTeachers() {
        return $this->db->fetchAll(
            "SELECT * FROM users WHERE role IN ('teacher', 'admin') ORDER BY first_name, last_name"
        );
    }
    
    public function getStudents() {
        return $this->db->fetchAll(
            "SELECT * FROM users WHERE role = 'student' ORDER BY first_name, last_name"
        );
    }
    
    public function getEnrolledCourses($userId) {
        return $this->db->fetchAll(
            "SELECT c.*, e.enrolled_at, e.progress_percentage, e.status 
             FROM courses c 
             JOIN enrollments e ON c.id = e.course_id 
             WHERE e.student_id = ? 
             ORDER BY e.enrolled_at DESC",
            [$userId]
        );
    }
    
    public function getCreatedCourses($userId) {
        return $this->db->fetchAll(
            "SELECT * FROM courses WHERE instructor_id = ? ORDER BY created_at DESC",
            [$userId]
        );
    }
    
    public function updateProfile($userId, $data) {
        $updateFields = [];
        $params = [];
        
        $fields = ['first_name', 'last_name', 'bio'];
        
        foreach ($fields as $field) {
            if (isset($data[$field])) {
                $updateFields[] = "$field = ?";
                $params[] = $data[$field];
            }
        }
        
        if (isset($data['password']) && !empty($data['password'])) {
            $updateFields[] = "password = ?";
            $params[] = password_hash($data['password'], PASSWORD_DEFAULT);
        }
        
        if (empty($updateFields)) {
            return false;
        }
        
        $params[] = $userId;
        
        $sql = "UPDATE users SET " . implode(', ', $updateFields) . " WHERE id = ?";
        $this->db->query($sql, $params);
        
        return true;
    }
    
    public function getStats($userId) {
        $stats = [];
        
        // Total courses enrolled
        $stats['enrolled_courses'] = $this->db->fetch(
            "SELECT COUNT(*) as count FROM enrollments WHERE student_id = ?",
            [$userId]
        )['count'];
        
        // Completed courses
        $stats['completed_courses'] = $this->db->fetch(
            "SELECT COUNT(*) as count FROM enrollments WHERE student_id = ? AND status = 'completed'",
            [$userId]
        )['count'];
        
        // Total lessons completed
        $stats['completed_lessons'] = $this->db->fetch(
            "SELECT COUNT(*) as count FROM lesson_progress WHERE student_id = ? AND is_completed = 1",
            [$userId]
        )['count'];
        
        // Average quiz score
        $stats['avg_quiz_score'] = $this->db->fetch(
            "SELECT AVG(score) as avg_score FROM quiz_attempts WHERE student_id = ? AND status = 'completed'",
            [$userId]
        )['avg_score'] ?? 0;
        
        return $stats;
    }
}
