<?php

class Quiz {
    private $db;
    
    public function __construct() {
        $this->db = Database::getInstance();
    }
    
    public function getById($id) {
        return $this->db->fetch("SELECT * FROM quizzes WHERE id = ?", [$id]);
    }
    
    public function getByCourseId($courseId) {
        return $this->db->fetchAll(
            "SELECT * FROM quizzes WHERE course_id = ? AND is_active = 1 ORDER BY created_at ASC",
            [$courseId]
        );
    }
    
    public function create($data) {
        $this->db->query(
            "INSERT INTO quizzes (course_id, title, description, time_limit_minutes, passing_score, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            [
                $data['course_id'],
                $data['title'],
                $data['description'] ?? null,
                $data['time_limit_minutes'] ?? 30,
                $data['passing_score'] ?? 70,
                $data['is_active'] ?? true
            ]
        );
        
        return $this->db->lastInsertId();
    }
    
    public function update($id, $data) {
        $updateFields = [];
        $params = [];
        
        $fields = ['title', 'description', 'time_limit_minutes', 'passing_score', 'is_active'];
        
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
        
        $sql = "UPDATE quizzes SET " . implode(', ', $updateFields) . " WHERE id = ?";
        $this->db->query($sql, $params);
        
        return true;
    }
    
    public function delete($id) {
        return $this->db->query("DELETE FROM quizzes WHERE id = ?", [$id]);
    }
    
    public function getQuestions($quizId) {
        return $this->db->fetchAll(
            "SELECT * FROM quiz_questions WHERE quiz_id = ? ORDER BY order_index ASC",
            [$quizId]
        );
    }
    
    public function getQuestionWithAnswers($questionId) {
        $question = $this->db->fetch(
            "SELECT * FROM quiz_questions WHERE id = ?",
            [$questionId]
        );
        
        if ($question) {
            $question['answers'] = $this->db->fetchAll(
                "SELECT * FROM quiz_answers WHERE question_id = ? ORDER BY order_index ASC",
                [$questionId]
            );
        }
        
        return $question;
    }
    
    public function addQuestion($data) {
        $this->db->query(
            "INSERT INTO quiz_questions (quiz_id, question, question_type, points, order_index) VALUES (?, ?, ?, ?, ?)",
            [
                $data['quiz_id'],
                $data['question'],
                $data['question_type'] ?? 'multiple_choice',
                $data['points'] ?? 1,
                $data['order_index'] ?? 0
            ]
        );
        
        return $this->db->lastInsertId();
    }
    
    public function addAnswer($data) {
        $this->db->query(
            "INSERT INTO quiz_answers (question_id, answer_text, is_correct, order_index) VALUES (?, ?, ?, ?)",
            [
                $data['question_id'],
                $data['answer_text'],
                $data['is_correct'] ?? false,
                $data['order_index'] ?? 0
            ]
        );
        
        return $this->db->lastInsertId();
    }
    
    public function startAttempt($quizId, $userId) {
        // Check if there's already an active attempt
        $existingAttempt = $this->db->fetch(
            "SELECT id FROM quiz_attempts WHERE quiz_id = ? AND student_id = ? AND status = 'in_progress'",
            [$quizId, $userId]
        );
        
        if ($existingAttempt) {
            return $existingAttempt['id'];
        }
        
        // Get total questions for this quiz
        $totalQuestions = $this->db->fetch(
            "SELECT COUNT(*) as count FROM quiz_questions WHERE quiz_id = ?",
            [$quizId]
        )['count'];
        
        // Create new attempt
        $this->db->query(
            "INSERT INTO quiz_attempts (quiz_id, student_id, total_questions) VALUES (?, ?, ?)",
            [$quizId, $userId, $totalQuestions]
        );
        
        return $this->db->lastInsertId();
    }
    
    public function submitAnswer($attemptId, $questionId, $answerId = null, $textResponse = null) {
        $question = $this->db->fetch(
            "SELECT * FROM quiz_questions WHERE id = ?",
            [$questionId]
        );
        
        if (!$question) {
            return false;
        }
        
        $isCorrect = false;
        $pointsEarned = 0;
        
        if ($question['question_type'] === 'multiple_choice' && $answerId) {
            $correctAnswer = $this->db->fetch(
                "SELECT id FROM quiz_answers WHERE question_id = ? AND is_correct = 1",
                [$questionId]
            );
            
            $isCorrect = $correctAnswer && $correctAnswer['id'] == $answerId;
            $pointsEarned = $isCorrect ? $question['points'] : 0;
        } elseif ($question['question_type'] === 'true_false' && $answerId) {
            $correctAnswer = $this->db->fetch(
                "SELECT id FROM quiz_answers WHERE question_id = ? AND is_correct = 1",
                [$questionId]
            );
            
            $isCorrect = $correctAnswer && $correctAnswer['id'] == $answerId;
            $pointsEarned = $isCorrect ? $question['points'] : 0;
        }
        // For short_answer, manual grading would be needed
        
        // Save response
        $this->db->query(
            "INSERT INTO quiz_responses (attempt_id, question_id, selected_answer_id, text_response, is_correct, points_earned) VALUES (?, ?, ?, ?, ?, ?)",
            [$attemptId, $questionId, $answerId, $textResponse, $isCorrect, $pointsEarned]
        );
        
        return true;
    }
    
    public function completeAttempt($attemptId) {
        $attempt = $this->db->fetch(
            "SELECT * FROM quiz_attempts WHERE id = ?",
            [$attemptId]
        );
        
        if (!$attempt) {
            return false;
        }
        
        // Calculate score
        $responses = $this->db->fetchAll(
            "SELECT * FROM quiz_responses WHERE attempt_id = ?",
            [$attemptId]
        );
        
        $totalPoints = 0;
        $earnedPoints = 0;
        $correctAnswers = 0;
        
        foreach ($responses as $response) {
            $question = $this->db->fetch(
                "SELECT points FROM quiz_questions WHERE id = ?",
                [$response['question_id']]
            );
            
            if ($question) {
                $totalPoints += $question['points'];
                $earnedPoints += $response['points_earned'];
                
                if ($response['is_correct']) {
                    $correctAnswers++;
                }
            }
        }
        
        $score = $totalPoints > 0 ? ($earnedPoints / $totalPoints) * 100 : 0;
        
        // Update attempt
        $this->db->query(
            "UPDATE quiz_attempts SET score = ?, correct_answers = ?, completed_at = NOW(), status = 'completed' WHERE id = ?",
            [$score, $correctAnswers, $attemptId]
        );
        
        return [
            'score' => round($score, 2),
            'total_questions' => $attempt['total_questions'],
            'correct_answers' => $correctAnswers,
            'total_points' => $totalPoints,
            'earned_points' => $earnedPoints
        ];
    }
    
    public function getAttempts($quizId, $userId) {
        return $this->db->fetchAll(
            "SELECT * FROM quiz_attempts WHERE quiz_id = ? AND student_id = ? ORDER BY started_at DESC",
            [$quizId, $userId]
        );
    }
    
    public function getAttempt($attemptId) {
        return $this->db->fetch(
            "SELECT * FROM quiz_attempts WHERE id = ?",
            [$attemptId]
        );
    }
    
    public function getAttemptResponses($attemptId) {
        return $this->db->fetchAll(
            "SELECT qr.*, qq.question, qq.question_type, qq.points, qa.answer_text as selected_answer
             FROM quiz_responses qr
             JOIN quiz_questions qq ON qr.question_id = qq.id
             LEFT JOIN quiz_answers qa ON qr.selected_answer_id = qa.id
             WHERE qr.attempt_id = ?
             ORDER BY qq.order_index ASC",
            [$attemptId]
        );
    }
    
    public function canTakeQuiz($quizId, $userId) {
        // Check if user is enrolled in the course
        $quiz = $this->getById($quizId);
        if (!$quiz) {
            return false;
        }
        
        $enrollment = $this->db->fetch(
            "SELECT id FROM enrollments WHERE course_id = ? AND student_id = ?",
            [$quiz['course_id'], $userId]
        );
        
        return $enrollment !== false;
    }
}

