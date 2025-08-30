<?php

class Course {
    private $db;
    
    public function __construct() {
        $this->db = Database::getInstance();
    }
    
    public function getAll($category = null, $instructor = null, $status = 'published', $limit = null, $offset = 0) {
        $sql = "SELECT c.*, u.first_name, u.last_name, cat.name as category_name 
                FROM courses c 
                LEFT JOIN users u ON c.instructor_id = u.id 
                LEFT JOIN categories cat ON c.category_id = cat.id";
        
        $conditions = [];
        $params = [];
        
        if ($category) {
            $conditions[] = "c.category_id = ?";
            $params[] = $category;
        }
        
        if ($instructor) {
            $conditions[] = "c.instructor_id = ?";
            $params[] = $instructor;
        }
        
        if ($status) {
            $conditions[] = "c.status = ?";
            $params[] = $status;
        }
        
        if (!empty($conditions)) {
            $sql .= " WHERE " . implode(' AND ', $conditions);
        }
        
        $sql .= " ORDER BY c.created_at DESC";
        
        if ($limit) {
            $sql .= " LIMIT ? OFFSET ?";
            $params[] = $limit;
            $params[] = $offset;
        }
        
        return $this->db->fetchAll($sql, $params);
    }
    
    public function getById($id) {
        return $this->db->fetch(
            "SELECT c.*, u.first_name, u.last_name, cat.name as category_name 
             FROM courses c 
             LEFT JOIN users u ON c.instructor_id = u.id 
             LEFT JOIN categories cat ON c.category_id = cat.id 
             WHERE c.id = ?",
            [$id]
        );
    }
    
    public function getBySlug($slug) {
        return $this->db->fetch(
            "SELECT c.*, u.first_name, u.last_name, cat.name as category_name 
             FROM courses c 
             LEFT JOIN users u ON c.instructor_id = u.id 
             LEFT JOIN categories cat ON c.category_id = cat.id 
             WHERE c.slug = ?",
            [$slug]
        );
    }
    
    public function create($data) {
        $slug = $this->generateSlug($data['title']);
        
        $this->db->query(
            "INSERT INTO courses (title, slug, description, short_description, instructor_id, category_id, price, is_premium, thumbnail, duration_hours, difficulty_level, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                $data['title'],
                $slug,
                $data['description'],
                $data['short_description'] ?? null,
                $data['instructor_id'],
                $data['category_id'] ?? null,
                $data['price'] ?? 0.00,
                $data['is_premium'] ?? false,
                $data['thumbnail'] ?? null,
                $data['duration_hours'] ?? 0,
                $data['difficulty_level'] ?? 'beginner',
                $data['status'] ?? 'draft'
            ]
        );
        
        return $this->db->lastInsertId();
    }
    
    public function update($id, $data) {
        $updateFields = [];
        $params = [];
        
        $fields = ['title', 'description', 'short_description', 'category_id', 'price', 'is_premium', 'thumbnail', 'duration_hours', 'difficulty_level', 'status'];
        
        foreach ($fields as $field) {
            if (isset($data[$field])) {
                $updateFields[] = "$field = ?";
                $params[] = $data[$field];
            }
        }
        
        if (isset($data['title'])) {
            $updateFields[] = "slug = ?";
            $params[] = $this->generateSlug($data['title'], $id);
        }
        
        if (empty($updateFields)) {
            return false;
        }
        
        $params[] = $id;
        
        $sql = "UPDATE courses SET " . implode(', ', $updateFields) . " WHERE id = ?";
        $this->db->query($sql, $params);
        
        return true;
    }
    
    public function delete($id) {
        return $this->db->query("DELETE FROM courses WHERE id = ?", [$id]);
    }
    
    public function getLessons($courseId) {
        return $this->db->fetchAll(
            "SELECT * FROM lessons WHERE course_id = ? ORDER BY order_index ASC",
            [$courseId]
        );
    }
    
    public function getQuizzes($courseId) {
        return $this->db->fetchAll(
            "SELECT * FROM quizzes WHERE course_id = ? AND is_active = 1 ORDER BY created_at ASC",
            [$courseId]
        );
    }
    
    public function getEnrollmentCount($courseId) {
        $result = $this->db->fetch(
            "SELECT COUNT(*) as count FROM enrollments WHERE course_id = ?",
            [$courseId]
        );
        return $result['count'];
    }
    
    public function isEnrolled($courseId, $userId) {
        $result = $this->db->fetch(
            "SELECT id FROM enrollments WHERE course_id = ? AND student_id = ?",
            [$courseId, $userId]
        );
        return $result !== false;
    }
    
    public function enroll($courseId, $userId) {
        // Check if already enrolled
        if ($this->isEnrolled($courseId, $userId)) {
            return ['success' => false, 'message' => 'Already enrolled in this course'];
        }
        
        $this->db->query(
            "INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)",
            [$userId, $courseId]
        );
        
        return ['success' => true, 'message' => 'Successfully enrolled'];
    }
    
    public function getProgress($courseId, $userId) {
        $course = $this->getById($courseId);
        $lessons = $this->getLessons($courseId);
        $completedLessons = $this->db->fetchAll(
            "SELECT lesson_id FROM lesson_progress WHERE student_id = ? AND lesson_id IN (SELECT id FROM lessons WHERE course_id = ?) AND is_completed = 1",
            [$userId, $courseId]
        );
        
        $totalLessons = count($lessons);
        $completedCount = count($completedLessons);
        
        $progress = $totalLessons > 0 ? ($completedCount / $totalLessons) * 100 : 0;
        
        // Update enrollment progress
        $this->db->query(
            "UPDATE enrollments SET progress_percentage = ? WHERE course_id = ? AND student_id = ?",
            [$progress, $courseId, $userId]
        );
        
        return [
            'total_lessons' => $totalLessons,
            'completed_lessons' => $completedCount,
            'progress_percentage' => round($progress, 2)
        ];
    }
    
    public function search($query, $limit = 10) {
        return $this->db->fetchAll(
            "SELECT c.*, u.first_name, u.last_name, cat.name as category_name 
             FROM courses c 
             LEFT JOIN users u ON c.instructor_id = u.id 
             LEFT JOIN categories cat ON c.category_id = cat.id 
             WHERE c.status = 'published' 
             AND (c.title LIKE ? OR c.description LIKE ? OR cat.name LIKE ?)
             ORDER BY c.created_at DESC 
             LIMIT ?",
            ["%$query%", "%$query%", "%$query%", $limit]
        );
    }
    
    private function generateSlug($title, $excludeId = null) {
        $slug = strtolower(trim(preg_replace('/[^A-Za-z0-9-]+/', '-', $title)));
        $slug = trim($slug, '-');
        
        $sql = "SELECT id FROM courses WHERE slug = ?";
        $params = [$slug];
        
        if ($excludeId) {
            $sql .= " AND id != ?";
            $params[] = $excludeId;
        }
        
        $existing = $this->db->fetch($sql, $params);
        
        if ($existing) {
            $counter = 1;
            do {
                $newSlug = $slug . '-' . $counter;
                $params[0] = $newSlug;
                $existing = $this->db->fetch($sql, $params);
                $counter++;
            } while ($existing);
            $slug = $newSlug;
        }
        
        return $slug;
    }
}
