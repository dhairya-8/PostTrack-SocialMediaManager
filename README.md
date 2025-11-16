📰 PostTrack – Smart Social Media Post Management System

A complete Client–Admin post management platform built with Django + MySQL, designed to streamline the creation, review, scheduling, and publishing of social media posts.

🚀 Overview

PostTrack bridges communication between clients and content managers/admins.
Clients submit post requests → Admins create drafts → Clients approve → Posts get scheduled & published.

Super Admin oversees everything.

✨ Features
👥 Role-Based Access
Role	Abilities
Super Admin	View everything (read-only), dashboard insights
Admin	Create/edit/delete posts, mark drafts as pending, manage assigned clients
Client	Submit post requests, review drafts, approve/reject, view published posts, manage profile
📌 Post Lifecycle

Draft → Pending → Approved → Published

Admins can create drafts, edit rejected posts, and submit drafts for review with a “Mark as Done” action.

📦 Modules
🔹 Client Portal

Submit post requests

View status of all requests

View feed of published posts

Review posts & give feedback

Profile + password management

Notification panel

🔹 Admin Panel

Create, edit, delete posts

Mark drafts as “Done” → moves to Pending

View rejected posts

Filter posts by status

Dashboard with activity insights

🔹 Super Admin Panel

Global overview of system activity

View all posts & feedback

Read-only permissions

🛠️ Tech Stack
Layer	Technology
Frontend	HTML5, CSS3, Bootstrap 5, JS, jQuery
Backend	Django (Python)
Database	MySQL
Auth System	Django Authentication + Custom Roles
Template Engine	Django Templates
Notifications	Custom Django-based notifier
📁 Folder Structure
PostTrack/
│── core/               # Authentication, dashboard, profiles, utilities
│── posts/              # Post creation, editing, feedback, lifecycle
│── users/              # Custom User model & ClientProfile
│── templates/          # HTML templates
│── static/             # CSS, JS, images
│── manage.py
│── requirements.txt
│── README.md
