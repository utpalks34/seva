# Smart Civic Feedback Management System (SCFMS)

## Project Overview
This project is a platform built to help citizens report local issues in their city (like potholes, garbage, or broken streetlights) and for government officials to track and fix them. The goal is to make communication between the public and the government faster and more organized.

We have two main sides to the platform:
1. Public Portal: Where anybody can go online, see current issues on a map, and submit a new complaint with a photo.
2. Government Dashboard: A secure login area where city workers can see incoming complaints, update their status, and manage the workflow.

## How it Works and Key Features

### Automated Sorting with Machine Learning
Instead of having a human manually read and sort every single complaint, the system does it automatically in the background when a citizen uploads a photo.
- Image Classification: We use a Hugging Face model to analyze the photo and figure out what category it belongs to (for example, whether it is a road issue or a garbage issue).
- Details and Priority: We use the Gemini Vision API to look at the photo and generate a clean title and description. It also gives the issue a severity score from 0 to 100, so government workers know immediately what needs to be fixed first.

### Real-Time Updates using WebSockets
We wanted the platform to feel fast and modern, so we used WebSockets (via Django Channels and Daphne). This means:
- Live Notifications: If a government worker clicks "Resolved" on a pothole issue, the citizen who reported it gets a notification popup on their screen instantly, without having to refresh the page.
- Chatbot: There is a live chat feature built in that answers questions in real-time.

### Tracking and Reports
The government dashboard comes with analytics tools. Officials can see heatmaps of where the most problems are happening in the city. They can also generate and download CSV or PDF reports for specific date ranges, which helps with keeping records and managing teams.

---

## How to Run the Project Locally

Because the project uses real-time WebSockets, you cannot use the normal standard Django runserver command. You have to use Daphne.

Here is the exact step-by-step to start it:

Step 1: Open your terminal and go into the project folder.
cd c:\Users\utpal\Desktop\seva\scfms_project

Step 2: Turn on the Python virtual environment.
venv\Scripts\activate

Step 3: Start the web server. You can just run the pre-made batch file:
.\start_daphne.bat
(Or if you want to type the full command, it is: venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 scfms_backend.asgi:application)

Step 4: Once the terminal says it is listening on port 8000, you are good to go. Keep the terminal open and go to your web browser. 
- For the public website, go to: http://127.0.0.1:8000/
- For the government login, go to: http://127.0.0.1:8000/go-login/
