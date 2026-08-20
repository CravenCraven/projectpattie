# Docker for Beginners: You Just Got Told to "Containerize Everything" and You Don't Even Know What a Container Is

## Table of Contents
1. [The Scenario](#the-scenario)
2. [The Problem](#the-problem)
3. [The Plan](#the-plan)
4. [The Walkthrough](#the-walkthrough)
5. [The Verification](#the-verification)
6. [The Recap](#the-recap)
7. [The Next Step](#the-next-step)

---

## The Scenario

It's your second month at NovaTech Solutions. You're the junior sysadmin. Life is good. You've been racking up small wins, resetting passwords, fixing printer issues, feeling like a tech hero. Then your manager drops this in the team Slack channel: "We're migrating all our internal apps to containers. Everyone needs to be up to speed on Docker by end of sprint."

You smile and give it a thumbs up emoji. Then you close Slack and quietly Google "what is a container."

Don't worry. That was me too. And honestly, that's most people. Nobody is born knowing this stuff, and the Docker documentation reads like it was written by someone who already knows Docker. So let's fix that right now.

---

## The Problem

Here's the actual business problem that Docker solves, and once you understand this, everything else clicks.

NovaTech has an internal inventory app. The dev team built it on their MacBooks using Python 3.11, Flask, and PostgreSQL 15. Works perfectly on their machines. Then they hand it off to you to deploy on the company's Ubuntu 22.04 server. You install Python, but the server has 3.9. You install Flask, but it pulls a different version of a dependency. You install PostgreSQL, but it's version 14. The app crashes. The dev says "it works on my machine." You say "cool, can I have your machine then?"

This is called the "works on my machine" problem, and it has been ruining the relationship between developers and operations teams since the beginning of time.

Docker fixes this by packaging the application AND its entire environment (the right Python version, the right libraries, the right database version, all of it) into a single portable unit called a container. You don't install anything on the server except Docker itself. The container brings everything it needs with it. It runs the same way on your laptop, on the Ubuntu server, on AWS, on your grandma's computer if she had Docker installed.

That's the pitch. Now let's actually do it.

---

## The Plan

Here's what we're going to do in this walkthrough, step by step:

1. Install Docker on Ubuntu, macOS, and Windows (pick your OS, skip the rest)
2. Understand images vs containers (the concept that trips everyone up)
3. Pull and run your first container
4. Run a real web server in a container
5. Build your own custom Docker image from scratch using a Dockerfile
6. Deploy a simple Python Flask app inside a container
7. Manage containers like a professional (stop, start, remove, logs, the works)

By the end of this post, you will have a working containerized application running on your machine and you'll actually understand what every piece does and why.

---

## The Walkthrough

### Step 1: Installing Docker

I'm covering all three operating systems. Find yours and skip the other two.

**Ubuntu / Debian Linux:**

First, remove any ancient Docker packages that might be lurking from previous attempts:

```bash
sudo apt-get remove docker docker-engine docker.io containerd runc
```

Now install the prerequisites and add Docker's official repository. Do not install Docker from the default Ubuntu repos. They're outdated and will cause you headaches later.

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Now add your user to the docker group so you don't have to type `sudo` every single time:

```bash
sudo usermod -aG docker $USER
```

Log out and log back in for this to take effect. Seriously, do it. Don't just open a new terminal and wonder why it doesn't work.

**macOS:**

Download Docker Desktop from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop). Open the `.dmg`, drag Docker to Applications, launch it. It'll ask for your password. Let it do its thing. When you see the whale icon in your menu bar, you're good.

**Windows:**

Download Docker Desktop from the same link. During installation, make sure "Use WSL 2 instead of Hyper-V" is checked. If you haven't enabled WSL 2 yet, Docker will walk you through it. Restart your computer when it asks. Yes, actually restart. Don't just close the dialog.

**Verify the install (all operating systems):**

```bash
docker --version
```

You should see something like `Docker version 27.x.x`. If you see "command not found," go back and re-read the install steps for your OS. Something got missed.

Now run the classic test:

```bash
docker run hello-world
```

If you see "Hello from Docker!" in your terminal, congratulations. Docker is installed, running, and just pulled and executed your first container. Let's talk about what actually just happened.

---

### Step 2: Images vs Containers (The Concept That Trips Everyone Up)

This is where most tutorials lose people, so I'm going to use an analogy that actually makes sense.

An **image** is a recipe. It's a set of instructions that says "here's what this application needs to run." It includes the operating system base, the installed software, the application code, the configuration files, everything. An image is read-only. You don't change it. You use it to create things.

A **container** is the meal you cooked from that recipe. It's a running instance of an image. You can have one image and spin up 10 containers from it. Each container runs independently. If one crashes, the others don't care.

When you ran `docker run hello-world`, here's what actually happened behind the scenes:

1. Docker checked your local machine for an image called `hello-world`. It didn't find one.
2. Docker pulled (downloaded) the `hello-world` image from Docker Hub, which is like the app store for Docker images.
3. Docker created a new container from that image.
4. The container ran, printed the message, and stopped.

That's the entire lifecycle: pull image, create container, run container.

---

### Step 3: Running a Real Web Server

The hello-world container is cute but useless. Let's run something real. We're going to spin up a full Nginx web server in one command.

```bash
docker run -d -p 8080:80 --name my-webserver nginx
```

Let me break down every flag because you need to understand what you're telling Docker to do:

- `docker run` — create and start a new container
- `-d` — run it in detached mode (in the background, so it doesn't hijack your terminal)
- `-p 8080:80` — map port 8080 on YOUR machine to port 80 inside the container. Nginx listens on port 80 by default. So when you visit localhost:8080, Docker routes that traffic into the container's port 80.
- `--name my-webserver` — give this container a human-readable name instead of Docker's random name generator (which gives you stuff like "angry_panda")
- `nginx` — the image to use

Open your browser and go to `http://localhost:8080`. You should see the Nginx welcome page. You just deployed a web server without installing Nginx, without configuring anything, without touching a single config file on your actual machine. The web server is running inside its own isolated environment.

Let's look at what's running:

```bash
docker ps
```

This shows all running containers. You'll see your `my-webserver` container, the ports it's using, how long it's been running, and the image it was created from.

Now let's look at the logs:

```bash
docker logs my-webserver
```

You'll see Nginx's access and error logs. Every time you refreshed that browser page, a log entry was created. This is how you troubleshoot containers in production.

Let's stop it:

```bash
docker stop my-webserver
```

And start it back up:

```bash
docker start my-webserver
```

And when you're done with it completely:

```bash
docker stop my-webserver
docker rm my-webserver
```

`stop` shuts it down. `rm` deletes the container entirely. The image is still on your machine though. To see all images:

```bash
docker images
```

---

### Step 4: Building Your Own Custom Image

Pulling pre-built images is great for existing software. But the real power of Docker is building your own images for your own applications. That's what your team at NovaTech actually needs you to do.

Let's build a containerized Python Flask application from scratch.

First, create a project directory:

```bash
mkdir ~/docker-flask-demo
cd ~/docker-flask-demo
```

Create the Flask application. This is a simple API that returns server information:

```bash
cat > app.py << 'EOF'
from flask import Flask, jsonify
import platform
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "message": "Hello from inside a Docker container!",
        "hostname": platform.node(),
        "python_version": platform.python_version(),
        "os": platform.platform(),
        "container_id": os.environ.get("HOSTNAME", "unknown")
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
EOF
```

Create the requirements file:

```bash
cat > requirements.txt << 'EOF'
flask==3.1.0
EOF
```

Now here's the important part. Create a `Dockerfile`. This is the recipe that tells Docker how to build your image. No file extension. Just `Dockerfile`.

```bash
cat > Dockerfile << 'EOF'
# Start from a lightweight Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first (this layer gets cached)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app.py .

# Tell Docker this container listens on port 5000
EXPOSE 5000

# The command to run when the container starts
CMD ["python", "app.py"]
EOF
```

Let me explain why the order matters. Docker builds images in layers. Each instruction in the Dockerfile creates a new layer. Docker caches these layers. If nothing changed in a layer, Docker skips rebuilding it. By copying `requirements.txt` and installing dependencies BEFORE copying the application code, Docker can cache the dependency layer. So when you change your Python code (which you'll do constantly), Docker doesn't have to reinstall all your pip packages every single time. It just rebuilds the layer that changed. This is a huge time saver and it's a best practice that separates people who know Docker from people who just copy-paste Dockerfiles.

Now build the image:

```bash
docker build -t novatech-flask-app:v1 .
```

- `-t novatech-flask-app:v1` — tag (name) the image. The `:v1` is the version tag. Always version your images.
- `.` — the build context. This tells Docker "all the files you need are in the current directory."

You'll see Docker execute each step in the Dockerfile. When it's done:

```bash
docker images | grep novatech
```

There's your image. Now run it:

```bash
docker run -d -p 5000:5000 --name novatech-api novatech-flask-app:v1
```

Hit `http://localhost:5000` in your browser. You'll see the JSON response from your Flask app, running inside a container, with the correct Python version, completely isolated from your host machine. Hit `http://localhost:5000/health` for the health check endpoint.

---

### Step 5: Real World Container Management

In a real production environment, you need to know more than just `docker run`. Here are the commands that will actually save your life.

**View running containers:**

```bash
docker ps
```

**View ALL containers (including stopped ones):**

```bash
docker ps -a
```

**Get inside a running container (for troubleshooting):**

```bash
docker exec -it novatech-api /bin/bash
```

This drops you into a shell inside the container. You can poke around, check files, test things. Type `exit` to leave. The container keeps running.

**View real-time logs:**

```bash
docker logs -f novatech-api
```

The `-f` flag follows the log output in real time, just like `tail -f`. Press Ctrl+C to stop watching.

**Check resource usage:**

```bash
docker stats novatech-api
```

This shows CPU, memory, network I/O, and disk I/O in real time. This is how you catch a container that's eating all your server's RAM at 3am.

**Copy files in and out of a container:**

```bash
# Copy a file FROM a container to your host
docker cp novatech-api:/app/app.py ./app-backup.py

# Copy a file FROM your host INTO a container
docker cp ./new-config.json novatech-api:/app/config.json
```

**Inspect a container's full configuration:**

```bash
docker inspect novatech-api
```

This dumps a massive JSON blob with every detail about the container: IP address, mounted volumes, environment variables, network settings, all of it. When something is broken and you can't figure out why, this is where you look.

**Clean up everything (nuclear option for your dev environment):**

```bash
# Stop all running containers
docker stop $(docker ps -q)

# Remove all stopped containers
docker rm $(docker ps -aq)

# Remove all unused images
docker image prune -a

# The "I give up, clean everything" command
docker system prune -a --volumes
```

That last command removes all stopped containers, all unused networks, all unused images, AND all unused volumes. Don't run this in production. Do run it on your dev machine when Docker is eating 40GB of disk space and you can't figure out why.

---

## The Verification

Let's make sure everything actually works end to end. Run through this checklist:

```bash
# 1. Check Docker is running
docker --version

# 2. Check your custom image exists
docker images | grep novatech

# 3. Run your container
docker run -d -p 5000:5000 --name verify-test novatech-flask-app:v1

# 4. Verify it's running
docker ps | grep verify-test

# 5. Test the endpoint
curl http://localhost:5000

# 6. Check logs
docker logs verify-test

# 7. Clean up
docker stop verify-test && docker rm verify-test
```

If every step returned what you expected, you're solid. If step 5 failed, check step 4. If step 4 shows the container exited, check `docker logs verify-test` for the error. 99% of the time it's a typo in the Dockerfile or a missing dependency in requirements.txt.

---

## The Recap

Here's what you just learned and what to remember:

**Images** are the blueprint. **Containers** are the running thing built from that blueprint. You can have many containers from one image.

**Dockerfile** is where you define how your image gets built. Order matters because of layer caching. Put things that change less (dependencies) before things that change often (your code).

**Port mapping** (`-p host:container`) connects the outside world to your container. Without it, your container is running but nobody can talk to it.

**Key commands you'll use every single day:**
- `docker build` — make an image
- `docker run` — make a container from an image
- `docker ps` — what's running
- `docker logs` — what happened
- `docker exec` — get inside a container
- `docker stop/rm` — shut it down and clean up

The real skill isn't memorizing commands. It's understanding the flow: write code, write Dockerfile, build image, run container, test, iterate. That's the Docker workflow, and everything else is just details.

---

## The Next Step

You can now containerize a single application. That's genuinely useful. But in the real world, applications don't run alone. Your Flask app needs a database. The database needs a cache layer. The cache needs a message queue. Now you've got 4 containers that all need to talk to each other, start in the right order, and share a network.

That's where **Docker Compose** comes in, and that's the next post in this series. We're going to take this Flask app and give it a PostgreSQL database, wire them together with a single YAML file, and spin up the whole stack with one command.

If you want to practice before the next post drops, try these challenges:

1. Modify the Flask app to add a `/version` endpoint that returns `{"version": "1.0.0"}`
2. Rebuild the image as `novatech-flask-app:v2`
3. Run both v1 and v2 at the same time on different ports
4. Compare the output of both by hitting their endpoints

That's Docker versioning in action. See you in the next one.
