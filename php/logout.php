<?php
require_once 'config/config.php';

$auth = new Auth();
$auth->logout();

redirect('/index.php');
?>
