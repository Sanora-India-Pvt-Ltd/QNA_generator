# Learning Management System (LMS)

A comprehensive Learning Management System built with PHP, featuring role-based access control, course management, progress tracking, and payment integration.

## Features

### 🎓 Core Features
- **User Management**: Registration, login, and role-based access control
- **Course Management**: Create, edit, and manage courses with lessons
- **Progress Tracking**: Monitor student progress through courses
- **Quiz System**: Create and take quizzes with automatic grading
- **Payment Integration**: Stripe payment processing for premium courses
- **Certificate Generation**: Automatic certificate generation upon course completion

### 👥 Role-Based Access
- **Admin**: Full system access, user management, reports
- **Teacher**: Create and manage courses, view student progress
- **Student**: Enroll in courses, track progress, take quizzes

### 💳 Payment Features
- Stripe payment integration
- Support for free and premium courses
- Payment history and refund management
- Secure payment processing

### 📊 Analytics & Reporting
- Student progress tracking
- Course completion statistics
- Payment analytics
- User activity monitoring

## Technology Stack

- **Backend**: PHP 7.4+
- **Database**: MySQL 5.7+
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Payment**: Stripe API
- **Email**: PHPMailer
- **Security**: Password hashing, CSRF protection, SQL injection prevention

## Installation

### Prerequisites
- PHP 7.4 or higher
- MySQL 5.7 or higher
- Composer
- Web server (Apache/Nginx)

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd lms
```

### Step 2: Install Dependencies
```bash
composer install
```

### Step 3: Database Setup
1. Create a MySQL database:
```sql
CREATE DATABASE lms_db;
```

2. Import the database schema:
```bash
mysql -u username -p lms_db < database/schema.sql
```

### Step 4: Environment Configuration
1. Copy the environment template:
```bash
cp env.example .env
```

2. Edit `.env` file with your configuration:
```env
# Database Configuration
DB_HOST=localhost
DB_NAME=lms_db
DB_USER=your_username
DB_PASS=your_password

# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Application Configuration
APP_URL=http://localhost/lms
APP_NAME="Learning Management System"
APP_ENV=development
```

### Step 5: Web Server Configuration

#### Apache Configuration
Create a `.htaccess` file in the root directory:
```apache
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ index.php [QSA,L]

# Security headers
Header always set X-Content-Type-Options nosniff
Header always set X-Frame-Options DENY
Header always set X-XSS-Protection "1; mode=block"
```

#### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/lms;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php7.4-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
```

### Step 6: File Permissions
```bash
chmod 755 -R .
chmod 777 -R uploads/
```

### Step 7: Access the Application
1. Open your web browser
2. Navigate to `http://localhost/lms`
3. Default admin credentials:
   - Username: `admin`
   - Password: `password`

## Usage

### For Administrators
1. **User Management**: Access `/admin/users.php` to manage users
2. **Course Management**: Access `/admin/courses.php` to manage all courses
3. **Payment Management**: Access `/admin/payments.php` to view payment history
4. **Reports**: Access `/admin/reports.php` for analytics and reports

### For Teachers
1. **Create Courses**: Access `/instructor/courses.php` to create new courses
2. **Manage Content**: Add lessons, quizzes, and course materials
3. **View Progress**: Monitor student progress and performance

### For Students
1. **Browse Courses**: View available courses on the homepage
2. **Enroll**: Enroll in free courses or purchase premium courses
3. **Learn**: Access course content and track progress
4. **Take Quizzes**: Complete assessments and earn certificates

## API Endpoints

### Authentication
- `POST /api/login.php` - User login
- `POST /api/register.php` - User registration
- `POST /api/logout.php` - User logout

### Courses
- `GET /api/courses.php` - List all courses
- `GET /api/courses/{id}.php` - Get course details
- `POST /api/courses.php` - Create new course (teacher/admin only)
- `PUT /api/courses/{id}.php` - Update course (teacher/admin only)

### Lessons
- `GET /api/lessons/{id}.php` - Get lesson content
- `POST /api/complete-lesson.php` - Mark lesson as complete

### Quizzes
- `GET /api/quizzes/{id}.php` - Get quiz questions
- `POST /api/quizzes/{id}/submit.php` - Submit quiz answers

### Payments
- `POST /api/payments/create.php` - Create payment intent
- `POST /api/payments/confirm.php` - Confirm payment

## Security Features

- **Password Hashing**: All passwords are hashed using PHP's `password_hash()`
- **CSRF Protection**: All forms include CSRF tokens
- **SQL Injection Prevention**: Prepared statements for all database queries
- **XSS Protection**: Input sanitization and output escaping
- **Session Security**: Secure session configuration
- **HTTPS Enforcement**: Secure headers and redirects

## Customization

### Styling
- Edit `assets/css/style.css` to customize the appearance
- Modify Bootstrap variables in the CSS file
- Add custom themes and color schemes

### Functionality
- Extend the core classes in the `src/` directory
- Add new features by creating additional PHP files
- Modify the database schema for new features

### Payment Integration
- The system uses Stripe by default
- To integrate other payment gateways, modify the `Payment` class
- Update the payment forms and API endpoints

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Verify database credentials in `.env`
   - Ensure MySQL service is running
   - Check database permissions

2. **Payment Issues**
   - Verify Stripe API keys
   - Check webhook configuration
   - Ensure HTTPS is enabled for payments

3. **File Upload Issues**
   - Check file permissions on uploads directory
   - Verify PHP upload settings
   - Check file size limits

4. **Email Not Working**
   - Verify SMTP settings
   - Check email credentials
   - Test with a simple email script

### Debug Mode
Enable debug mode by setting `APP_ENV=development` in `.env` file.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the troubleshooting section

## Changelog

### Version 1.0.0
- Initial release
- Basic LMS functionality
- User management
- Course management
- Payment integration
- Quiz system
- Progress tracking

## Roadmap

### Version 1.1.0 (Planned)
- Advanced analytics dashboard
- Mobile app support
- Video conferencing integration
- Advanced quiz types
- Gamification features

### Version 1.2.0 (Planned)
- Multi-language support
- Advanced reporting
- API improvements
- Performance optimizations
- Enhanced security features
