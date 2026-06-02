async function login() {
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;
  const response = await fetch("/api/login", {
   
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  });
  const data = await response.json();
  document.getElementById("message").innerText = data.message;

  if (data.token) {
    localStorage.setItem("token", data.token); 
    window.location.href = "/dashboard"; 
  }
}

async function signup() {
  const username = document.getElementById("username").value;
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const dateofbirth = document.getElementById("dateofbirth").value;

  if (!gender) {
    document.getElementById("message").innerText = "Please select gender";
    return;
  }

  const response = await fetch("/api/signup", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username,
      email,
      password,
      dateofbirth,
    }),
  });
  const data = await response.json();
  document.getElementById("message").innerText = data.message;
  if (response.ok) {
    setTimeout(() => {
      window.location.href = "/";
    }, 1500);
  }
}

async function getprofile() {
  const token = localStorage.getItem("token");
  if (!token) {
    document.getElementById("profile").innerText =
      "Not logged in. Redirecting...";
    setTimeout(() => {
      window.location.href = "/";
    }, 1500);
    return;
  }
  const response = await fetch("/api/profile", {
   
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  const data = await response.json();
  if (response.ok) {
    document.getElementById("profile").innerHTML = `
            <strong>${data.username}</strong><br>
            Email: ${data.email}<br>
            Date of Birth: ${data.dateofbirth}
        `;
  } else {
    document.getElementById("profile").innerText = data.message;
    if (response.status === 401) {
      localStorage.removeItem("token");
      setTimeout(() => {
        window.location.href = "/";
      }, 2000);
    }
  }
}
