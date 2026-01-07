import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/LoginSignup.css";

export default function LoginSignup() {
  const [action, setAction] = useState("Sign Up");

  // Added states (no UI change)
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [errors, setErrors] = useState({});
  const navigate = useNavigate();

  // Validation logic
  const validateForm = () => {
    let newErrors = {};

    if (action === "Sign Up") {
      if (!name.trim()) {
        newErrors.name = "Name is required";
      } else if (name.length < 3) {
        newErrors.name = "Name must be at least 3 characters";
      }
    }

    if (!email) {
      newErrors.email = "Email is required";
    } else if (!/^\S+@\S+\.\S+$/.test(email)) {
      newErrors.email = "Enter a valid email";
    }

    if (!password) {
      newErrors.password = "Password is required";
    } else if (action === "Sign Up" && password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Submit handler
  const handleSubmit = () => {
    if (!validateForm()) return;

    if (action === "Sign Up") {
      alert("Signup successful");
    } else {
      alert("Login successful");
    }
    localStorage.setItem("isLoggedIn", "true");
    navigate("/home");
  };

  return (
    <div className="container">
      <div className="head">
        <div className="header">{action}</div>
        <div className="underline"></div>
      </div>
      <div className="submit-container">
        <button
          className={action === "Log In" ? "submit gray" : "submit"}
          onClick={() => setAction("Sign Up")}
        >
          Sign Up
        </button>

        <button
          className={action === "Sign Up" ? "submit gray" : "submit"}
          onClick={() => setAction("Log In")}
        >
          Log In
        </button>
      </div>

      {action === "Log In" ? (
        <div></div>
      ) : (
        <>
          <div className="input">
            <img src="" />
            <input
              type="text"
              placeholder="Name"
              className="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          {errors.name && <p className="error">{errors.name}</p>}
        </>
      )}

      <div className="input">
        <img src="" />
        <input
          type="email"
          placeholder="Email"
          className="text"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      {errors.email && <p className="error">{errors.email}</p>}

      <div className="input">
        <img src="" />
        <input
          type="password"
          placeholder="Password"
          className="text"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      {errors.password && <p className="error">{errors.password}</p>}

      {action === "Sign Up" ? (
        <div></div>
      ) : (
        <div className="forget-password">
          Forget Password?{" "}
          <span>
            <a href="#click">Click here!</a>
          </span>
        </div>
      )}

      <button className="submit full" onClick={handleSubmit}>
        {action}
      </button>
    </div>
  );
}
