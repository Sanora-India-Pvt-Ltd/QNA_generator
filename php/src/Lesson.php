<?php

class Lesson {
    private $db;
    
    public function __construct() {
        $this->db = Database::getInstance();
    }
    
    public function getById($id) {
        return $this->db->fetch("SELECT * FROM lessons WHERE id = ?", [$id]);
    }
    
    public function getByCourseId($courseId) {
        return $this->db->fetchAll(
            "SELECT * FROM lessons WHERE course_id = ? ORDER BY order_index ASC",
            [$courseId]
        );
    }
    
    public function create($data) {
        $this->db->query(
            "INSERT INTO lessons (course_id, title, content, video_url, duration_minutes, order_index, is_free) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                $data['course_id'],
                $data['title'],
                $data['content'] ?? null,
                $data['video_url'] ?? null,
                $data['duration_minutes'] ?? 0,
                $data['order_index'] ?? 0,
                $data['is_free'] ?? false
            ]
        );
        
        return $this->db->lastInsertId();
    }
    
    public function update($id, $data) {
        $updateFields = [];
        $params = [];
        
        $fields = ['title', 'content', 'video_url', 'duration_minutes', 'order_index', 'is_free'];
        
        foreach ($fields as $field) {
            if (isset($data[$field])) {
                $updateFields[] = "$field = ?";
                $params[] = $data[$field];
            }
        }
        
        if (empty($updateFields)) {
            return false;
        }
        
        $params[] = $id;
        
        $sql = "UPDATE lessons SET " . implode(', ', $updateFields) . " WHERE id = ?";
        $this->db->query($sql, $params);
        
        return true;
    }
    
    public function delete($id) {
        return $this->db->query("DELETE FROM lessons WHERE id = ?", [$id]);
    }
    
    public function markAsCompleted($lessonId, $userId) {
        // Check if already completed
        $existing = $this->db->fetch(
            "SELECT id FROM lesson_progress WHERE lesson_id = ? AND student_id = ?",
            [$lessonId, $userId]
        );
        
        if ($existing) {
            // Update existing record
            $this->db->query(
                "UPDATE lesson_progress SET is_completed = 1, completed_at = NOW() WHERE lesson_id = ? AND student_id = ?",
                [$lessonId, $userId]
            );
        } else {
            // Create new record
            $this->db->query(
                "INSERT INTO lesson_progress (lesson_id, student_id, is_completed, completed_at) VALUES (?, ?, 1, NOW())",
                [$lessonId, $userId]
            );
        }
        
        return true;
    }
    
    public function isCompleted($lessonId, $userId) {
        $result = $this->db->fetch(
            "SELECT is_completed FROM lesson_progress WHERE lesson_id = ? AND student_id = ?",
            [$lessonId, $userId]
        );
        
        return $result && $result['is_completed'] == 1;
    }
    
    public function getProgress($courseId, $userId) {
        $lessons = $this->getByCourseId($courseId);
        $completedLessons = $this->db->fetchAll(
            "SELECT lesson_id FROM lesson_progress WHERE student_id = ? AND lesson_id IN (SELECT id FROM lessons WHERE course_id = ?) AND is_completed = 1",
            [$userId, $courseId]
        );
        
        $totalLessons = count($lessons);
        $completedCount = count($completedLessons);
        
        return [
            'total_lessons' => $totalLessons,
            'completed_lessons' => $completedCount,
            'progress_percentage' => $totalLessons > 0 ? round(($completedCount / $totalLessons) * 100, 2) : 0
        ];
    }
    
    public function getNextLesson($courseId, $currentLessonId, $userId) {
        $currentLesson = $this->getById($currentLessonId);
        if (!$currentLesson) {
            return null;
        }
        
        $nextLesson = $this->db->fetch(
            "SELECT * FROM lessons WHERE course_id = ? AND order_index > ? ORDER BY order_index ASC LIMIT 1",
            [$courseId, $currentLesson['order_index']]
        );
        
        return $nextLesson;
    }
    
    public function getPreviousLesson($courseId, $currentLessonId, $userId) {
        $currentLesson = $this->getById($currentLessonId);
        if (!$currentLesson) {
            return null;
        }
        
        $previousLesson = $this->db->fetch(
            "SELECT * FROM lessons WHERE course_id = ? AND order_index < ? ORDER BY order_index DESC LIMIT 1",
            [$courseId, $currentLesson['order_index']]
        );
        
        return $previousLesson;
    }
    
    public function canAccess($lessonId, $userId) {
        $lesson = $this->getById($lessonId);
        if (!$lesson) {
            return false;
        }
        
        // If lesson is free, anyone can access
        if ($lesson['is_free']) {
            return true;
        }
        
        // Check if user is enrolled in the course
        $enrollment = $this->db->fetch(
            "SELECT id FROM enrollments WHERE course_id = ? AND student_id = ?",
            [$lesson['course_id'], $userId]
        );
        
        return $enrollment !== false;
    }
    
    public function updateTimeSpent($lessonId, $userId, $minutes) {
        $existing = $this->db->fetch(
            "SELECT id, time_spent_minutes FROM lesson_progress WHERE lesson_id = ? AND student_id = ?",
            [$lessonId, $userId]
        );
        
        if ($existing) {
            $newTime = $existing['time_spent_minutes'] + $minutes;
            $this->db->query(
                "UPDATE lesson_progress SET time_spent_minutes = ? WHERE lesson_id = ? AND student_id = ?",
                [$newTime, $lessonId, $userId]
            );
        } else {
            $this->db->query(
                "INSERT INTO lesson_progress (lesson_id, student_id, time_spent_minutes) VALUES (?, ?, ?)",
                [$lessonId, $userId, $minutes]
            );
        }
        
        return true;
    }
}

