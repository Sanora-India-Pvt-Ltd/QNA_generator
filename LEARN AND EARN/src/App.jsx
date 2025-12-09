import React, { useEffect, useState } from "react";
import Desktop1 from "./Desktop1";

export default function App(props) {
	const [isAuthenticated, setIsAuthenticated] = useState(false);
	const [isLogin, setIsLogin] = useState(true);
	const [emailOrPhone, setEmailOrPhone] = useState("");
	const [phoneNumber, setPhoneNumber] = useState("");
	const [password, setPassword] = useState("");
	const [firstName, setFirstName] = useState("");
	const [lastName, setLastName] = useState("");
	const [gender, setGender] = useState("");
	const [emailOtp, setEmailOtp] = useState("");
	const [phoneOtp, setPhoneOtp] = useState("");
	const [emailVerificationToken, setEmailVerificationToken] = useState("");
	const [phoneVerificationToken, setPhoneVerificationToken] = useState("");
	const [emailOtpStatus, setEmailOtpStatus] = useState("idle"); // idle | sending | sent | verifying | verified | error
	const [phoneOtpStatus, setPhoneOtpStatus] = useState("idle"); // idle | sending | sent | verifying | verified | error
	const [googleLoading, setGoogleLoading] = useState(false);
	const [forgotOpen, setForgotOpen] = useState(false);
	const [forgotMode, setForgotMode] = useState("email"); // email | phone
	const [forgotValue, setForgotValue] = useState("");
	const [forgotLoading, setForgotLoading] = useState(false);
	const [forgotMessage, setForgotMessage] = useState("");
	const [forgotStep, setForgotStep] = useState("send"); // send | verify | reset
	const [forgotOtp, setForgotOtp] = useState(["", "", "", "", "", ""]);
	const [forgotOtpIndex, setForgotOtpIndex] = useState(0);
	const [forgotVerificationToken, setForgotVerificationToken] = useState("");
	const [newPassword, setNewPassword] = useState("");
	const [confirmPassword, setConfirmPassword] = useState("");
	const [resendTimer, setResendTimer] = useState(0);
	const [showNewPassword, setShowNewPassword] = useState(false);
	const [showConfirmPassword, setShowConfirmPassword] = useState(false);
	const [showPassword, setShowPassword] = useState(false);
	const [message, setMessage] = useState("");
	const [error, setError] = useState("");
	const [loading, setLoading] = useState(false);

	const API_BASE = "https://api.sanoraindia.com";
	const GOOGLE_CLIENT_ID = "804599806902-fdh2279lqo96btm255232u83ae6je06p.apps.googleusercontent.com";

	// Helper function to handle API calls with proper error handling
	const apiCall = async (url, options = {}) => {
		const controller = new AbortController();
		let timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

		try {
			const res = await fetch(url, {
				...options,
				signal: controller.signal,
				headers: {
					"Content-Type": "application/json",
					...options.headers,
				},
			});

			clearTimeout(timeoutId);

			// Check if response is ok
			if (!res.ok) {
				let errorMessage = `Request failed with status ${res.status}`;
				try {
					const errorJson = await res.json();
					errorMessage = errorJson.message || errorJson.error || errorMessage;
				} catch {
					// If response is not JSON, use status text
					errorMessage = res.statusText || errorMessage;
				}
				throw new Error(errorMessage);
			}

			// Parse JSON response
			let json;
			try {
				json = await res.json();
			} catch (parseError) {
				throw new Error("Invalid response from server. Please try again.");
			}

			return { res, json };
		} catch (error) {
			clearTimeout(timeoutId);
			if (error.name === 'AbortError') {
				throw new Error("Request timeout. Please check your internet connection and try again.");
			}
			if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError') || error.message === 'Failed to fetch') {
				throw new Error("Network error. Please check your internet connection and try again.");
			}
			if (error.message.includes('CORS')) {
				throw new Error("Connection error. Please try again later.");
			}
			throw error;
		}
	};

	// Check if user is authenticated on mount
	useEffect(() => {
		const accessToken = localStorage.getItem("accessToken");
		if (accessToken) {
			setIsAuthenticated(true);
		}
	}, []);

	// Handle Google OAuth callback
	useEffect(() => {
		// Check if we're returning from Google OAuth
		const urlParams = new URLSearchParams(window.location.search);
		const token = urlParams.get('token');
		const name = urlParams.get('name');
		const email = urlParams.get('email');

		if (token) {
			// We're returning from Google OAuth redirect
			handleGoogleCallback(token, name, email);
			// Clean up URL
			window.history.replaceState({}, document.title, window.location.pathname);
		}
	}, []);

	const handleGoogleCallback = async (token, name, email) => {
		setGoogleLoading(true);
		setError("");
		setMessage("");
		try {
			const { json } = await apiCall(`${API_BASE}/api/auth/verify-google-token`, {
				method: "POST",
				body: JSON.stringify({ token })
			});
			
			if (!json.success) {
				throw new Error(json.message || "Google sign-in verification failed");
			}
			const { accessToken, refreshToken, user } = json.data;
			localStorage.setItem("accessToken", accessToken);
			localStorage.setItem("refreshToken", refreshToken);
			setMessage(`Welcome, ${user?.name || name || "user"}!`);
			setIsAuthenticated(true);
		} catch (err) {
			setError(err.message || "Google sign-in failed");
		} finally {
			setGoogleLoading(false);
		}
	};

	const emailValid = /\S+@gmail\.com$/i.test(emailOrPhone.trim());
	const phoneDigits = phoneNumber.replace(/\D/g, "");
	const phoneValid = phoneDigits.length === 10;
	const emailOtpValid = /^\d{6}$/.test(emailOtp);
	const phoneOtpValid = /^\d{6}$/.test(phoneOtp);

	// Load Google Sign-In JavaScript SDK and render button
	useEffect(() => {
		if (document.getElementById("google-signin-script")) {
			// Script already loaded, initialize
			if (window.google?.accounts?.id) {
				initializeGoogleSignIn();
			}
			return;
		}
		
		const script = document.createElement("script");
		script.src = "https://accounts.google.com/gsi/client";
		script.async = true;
		script.defer = true;
		script.id = "google-signin-script";
		script.onload = () => {
			if (window.google?.accounts?.id) {
				initializeGoogleSignIn();
			}
		};
		document.head.appendChild(script);
	}, []);

	// Re-initialize Google button when switching to login mode
	useEffect(() => {
		if (isLogin && window.google?.accounts?.id) {
			// Small delay to ensure DOM is updated
			setTimeout(() => {
				initializeGoogleSignIn();
			}, 100);
		}
	}, [isLogin]);

	const initializeGoogleSignIn = () => {
		if (!window.google?.accounts?.id) return;
		
		window.google.accounts.id.initialize({
			client_id: GOOGLE_CLIENT_ID,
			callback: handleGoogleCredentialResponse,
			ux_mode: "popup" // Use popup mode for JSON token response
		});

		// Render Google button into our custom container
		const buttonContainer = document.getElementById("google-signin-button");
		if (buttonContainer) {
			// Clear existing content
			buttonContainer.innerHTML = '';
			window.google.accounts.id.renderButton(buttonContainer, {
				type: "standard",
				theme: "outline",
				size: "large",
				text: "signin_with",
				width: "100%"
			});
		}
	};

	const handleGoogleCredentialResponse = async (response) => {
		if (!response?.credential) {
			setError("No credential received from Google");
			setGoogleLoading(false);
			return;
		}

		setGoogleLoading(true);
		setError("");
		setMessage("");

		try {
			// The credential is a JWT token (JSON Web Token) returned as JSON
			// Send it to backend for verification
			const { json } = await apiCall(`${API_BASE}/api/auth/verify-google-token`, {
				method: "POST",
				body: JSON.stringify({ token: response.credential })
			});

			if (!json.success) {
				throw new Error(json.message || "Google sign-in verification failed");
			}

			// Store tokens and user data from JSON response
			const { accessToken, refreshToken, user } = json.data;
			localStorage.setItem("accessToken", accessToken);
			localStorage.setItem("refreshToken", refreshToken);
			setMessage(`Welcome, ${user?.name || "user"}!`);
			setIsAuthenticated(true);
		} catch (err) {
			setError(err.message || "Google sign-in failed");
		} finally {
			setGoogleLoading(false);
		}
	};

	const handleGoogleSignInRedirect = () => {
		// This will be handled by the rendered Google button
		// Just show loading state
		setGoogleLoading(true);
	};

	const handleSendEmailOtp = async () => {
		if (!emailValid) {
			setError("Enter a valid @gmail.com email first.");
			return;
		}
		setError("");
		setMessage("");
		setEmailOtpStatus("sending");
		try {
			const { json } = await apiCall(`${API_BASE}/api/auth/send-otp-signup`, {
				method: "POST",
				body: JSON.stringify({ email: emailOrPhone.trim().toLowerCase() })
			});
			
			if (!json.success) {
				throw new Error(json.message || "Failed to send email OTP");
			}
			setEmailOtpStatus("sent");
			setMessage("Email OTP sent. Check your inbox.");
		} catch (err) {
			setEmailOtpStatus("error");
			setError(err.message || "Failed to send email OTP");
		}
	};

	const handleVerifyEmailOtp = async () => {
		if (!emailOtpValid) {
			setError("Enter the 6-digit email OTP.");
			return;
		}
		setError("");
		setMessage("");
		setEmailOtpStatus("verifying");
		try {
			const { json } = await apiCall(`${API_BASE}/api/auth/verify-otp-signup`, {
				method: "POST",
				body: JSON.stringify({ email: emailOrPhone.trim().toLowerCase(), otp: emailOtp })
			});
			
			if (!json.success) {
				throw new Error(json.message || "Email OTP verification failed");
			}
			setEmailVerificationToken(json.data?.emailVerificationToken || "");
			setEmailOtpStatus("verified");
			setMessage("Email verified.");
		} catch (err) {
			setEmailOtpStatus("error");
			setError(err.message || "Email OTP verification failed");
		}
	};

	const handleSendPhoneOtp = async () => {
		if (!phoneValid) {
			setError("Enter a valid 10-digit phone number first.");
			return;
		}
		setError("");
		setMessage("");
		setPhoneOtpStatus("sending");
		try {
			const { json } = await apiCall(`${API_BASE}/api/auth/send-phone-otp-signup`, {
				method: "POST",
				body: JSON.stringify({ phone: `+91${phoneDigits}` })
			});
			
			if (!json.success) {
				throw new Error(json.message || "Failed to send phone OTP");
			}
			setPhoneOtpStatus("sent");
			setMessage("Phone OTP sent. Check your SMS.");
		} catch (err) {
			setPhoneOtpStatus("error");
			setError(err.message || "Failed to send phone OTP");
		}
	};

	const handleVerifyPhoneOtp = async () => {
		if (!phoneOtpValid) {
			setError("Enter the 6-digit phone OTP.");
			return;
		}
		setError("");
		setMessage("");
		setPhoneOtpStatus("verifying");
		try {
			const { json } = await apiCall(`${API_BASE}/api/auth/verify-phone-otp-signup`, {
				method: "POST",
				body: JSON.stringify({ phone: `+91${phoneDigits}`, otp: phoneOtp })
			});
			
			if (!json.success) {
				throw new Error(json.message || "Phone OTP verification failed");
			}
			setPhoneVerificationToken(json.data?.phoneVerificationToken || "");
			setPhoneOtpStatus("verified");
			setMessage("Phone verified.");
		} catch (err) {
			setPhoneOtpStatus("error");
			setError(err.message || "Phone OTP verification failed");
		}
	};

	const handleSubmit = async (e) => {
		e.preventDefault();
		setMessage("");
		setError("");
		setLoading(true);

		try {
			if (isLogin) {
				const body = emailOrPhone.includes("@")
					? { email: emailOrPhone.trim(), password }
					: { phoneNumber: emailOrPhone.trim(), password };

				const { json } = await apiCall(`${API_BASE}/api/auth/login`, {
					method: "POST",
					body: JSON.stringify(body)
				});

				if (!json.success) {
					throw new Error(json.message || "Login failed");
				}

				const { accessToken, refreshToken, user } = json.data;
				localStorage.setItem("accessToken", accessToken);
				localStorage.setItem("refreshToken", refreshToken);
				setMessage(`Welcome back, ${user?.name || "user"}!`);
				setIsAuthenticated(true);
			} else {
				// Basic required fields for signup
				if (!emailVerificationToken || !phoneVerificationToken) {
					throw new Error("Verify both email and phone OTP before signing up.");
				}
				if (password !== confirmPassword) {
					throw new Error("Passwords do not match");
				}
				const signupBody = {
					email: emailOrPhone.trim(),
					password,
					confirmPassword: confirmPassword,
					firstName: firstName.trim(),
					lastName: lastName.trim(),
					phoneNumber: `+91${phoneDigits}`,
					gender: gender || "Prefer not to say",
					emailVerificationToken: emailOtpValid ? emailOtp : "",
					phoneVerificationToken: phoneOtpValid ? phoneOtp : ""
				};

				const { json } = await apiCall(`${API_BASE}/api/auth/signup`, {
					method: "POST",
					body: JSON.stringify(signupBody)
				});

				if (!json.success) {
					throw new Error(json.message || "Signup failed");
				}

				const { accessToken, refreshToken, user } = json.data;
				localStorage.setItem("accessToken", accessToken);
				localStorage.setItem("refreshToken", refreshToken);
				setMessage(`Account created for ${user?.name || "user"}!`);
				setIsAuthenticated(true);
			}
		} catch (err) {
			setError(err.message || "Something went wrong");
		} finally {
			setLoading(false);
		}
	};

	const handleGoogleSignIn = () => {
		setError("");
		setMessage("");
		setGoogleLoading(true);
		// Use redirect flow - more reliable and works with JSON response
		handleGoogleSignInRedirect();
	};

	const handleForgotPassword = () => {
		setForgotOpen(true);
		setForgotMode("email");
		setForgotValue("");
		setForgotMessage("");
		setError("");
		setForgotStep("send");
		setForgotOtp(["", "", "", "", "", ""]);
		setForgotOtpIndex(0);
		setForgotVerificationToken("");
		setNewPassword("");
		setConfirmPassword("");
		setResendTimer(0);
	};

	// Password generator based on username
	const generatePassword = () => {
		const username = firstName.trim() || emailOrPhone.split("@")[0] || "user";
		const specialChars = "!@#$%^&*";
		const numbers = "0123456789";
		const randomSpecial = specialChars[Math.floor(Math.random() * specialChars.length)];
		const randomNumber = numbers[Math.floor(Math.random() * numbers.length)];
		const randomUpper = String.fromCharCode(65 + Math.floor(Math.random() * 26));
		const randomLower = String.fromCharCode(97 + Math.floor(Math.random() * 26));
		
		// Create password: username + special + number + random chars
		const base = username.substring(0, 4).toLowerCase();
		const generated = base + randomUpper + randomLower + randomSpecial + randomNumber + 
			String.fromCharCode(97 + Math.floor(Math.random() * 26)) + 
			numbers[Math.floor(Math.random() * numbers.length)];
		
		setPassword(generated);
		// Also set confirm password in sign-up
		setConfirmPassword(generated);
	};

	const handleForgotSubmit = async () => {
		setForgotMessage("");
		setError("");

		const val = forgotValue.trim();
		const isEmail = forgotMode === "email";
		const isPhone = forgotMode === "phone";

		if (!val) {
			setError("Please enter your email or phone.");
			return;
		}

		const body = {};
		if (isEmail) {
			body.email = val.toLowerCase();
		} else if (isPhone) {
			const digits = val.replace(/\D/g, "");
			if (digits.length !== 10) {
				setError("Enter a valid 10-digit phone number.");
				return;
			}
			body.phone = `+91${digits}`;
		}

		setForgotLoading(true);
		try {
			const { json } = await apiCall(`${API_BASE}/api/auth/forgot-password/send-otp`, {
				method: "POST",
				body: JSON.stringify(body)
			});
			
			if (!json.success) {
				throw new Error(json.message || "Failed to send OTP");
			}
			setForgotMessage("OTP sent. Please check your email/phone.");
			setForgotStep("verify");
			setResendTimer(60); // 60 second timer
			// Start countdown
			const interval = setInterval(() => {
				setResendTimer((prev) => {
					if (prev <= 1) {
						clearInterval(interval);
						return 0;
					}
					return prev - 1;
				});
			}, 1000);
		} catch (err) {
			setError(err.message || "Failed to send OTP");
		} finally {
			setForgotLoading(false);
		}
	};

	const handleForgotOtpChange = (index, value) => {
		if (!/^\d*$/.test(value)) return; // Only digits
		const newOtp = [...forgotOtp];
		newOtp[index] = value.slice(-1); // Only last digit
		setForgotOtp(newOtp);
		
		// Auto-focus next input
		if (value && index < 5) {
			setForgotOtpIndex(index + 1);
			const nextInput = document.getElementById(`forgot-otp-${index + 1}`);
			if (nextInput) nextInput.focus();
		}
	};

	const handleForgotOtpKeyDown = (index, e) => {
		if (e.key === "Backspace" && !forgotOtp[index] && index > 0) {
			setForgotOtpIndex(index - 1);
			const prevInput = document.getElementById(`forgot-otp-${index - 1}`);
			if (prevInput) prevInput.focus();
		}
	};

	const handleVerifyForgotOtp = async () => {
		const otpString = forgotOtp.join("");
		if (otpString.length !== 6) {
			setError("Please enter the complete 6-digit OTP.");
			return;
		}

		setForgotLoading(true);
		setError("");
		try {
			const body = forgotMode === "email" 
				? { email: forgotValue.trim().toLowerCase(), otp: otpString }
				: { phone: `+91${forgotValue.replace(/\D/g, "")}`, otp: otpString };

			const { json } = await apiCall(`${API_BASE}/api/auth/forgot-password/verify-otp`, {
				method: "POST",
				body: JSON.stringify(body)
			});
			
			if (!json.success) {
				throw new Error(json.message || "Invalid OTP");
			}
			setForgotVerificationToken(json.data?.verificationToken || "");
			setForgotStep("reset");
			setForgotMessage("");
		} catch (err) {
			setError(err.message || "OTP verification failed");
		} finally {
			setForgotLoading(false);
		}
	};

	const handleResetPassword = async () => {
		if (!newPassword || newPassword.length < 6) {
			setError("Password must be at least 6 characters.");
			return;
		}
		if (newPassword !== confirmPassword) {
			setError("Passwords do not match.");
			return;
		}
		if (!forgotVerificationToken) {
			setError("Verification token missing. Please start over.");
			return;
		}

		setForgotLoading(true);
		setError("");
		try {
			const { json } = await apiCall(`${API_BASE}/api/auth/forgot-password/reset`, {
				method: "POST",
				body: JSON.stringify({
					verificationToken: forgotVerificationToken,
					password: newPassword,
					confirmPassword: confirmPassword
				})
			});
			
			if (!json.success) {
				throw new Error(json.message || "Password reset failed");
			}
			setForgotMessage("Password reset successfully! You can now login.");
			setTimeout(() => {
				setForgotOpen(false);
				setIsLogin(true);
			}, 2000);
		} catch (err) {
			setError(err.message || "Password reset failed");
		} finally {
			setForgotLoading(false);
		}
	};

	const handleCreateAccount = () => {
		setIsLogin(false);
	};

	// If user is authenticated, show home page
	if (isAuthenticated) {
		return <Desktop1 />;
	}

	// Otherwise, show login/signup form
	return (
		<div className="min-h-screen bg-[#F0F2F5] relative overflow-hidden">
			{/* Decorative ellipses */}
			<div className="absolute -top-24 -right-24 w-[360px] h-[360px] rounded-full bg-[#F3E4DB] opacity-90 pointer-events-none" />
			<div className="absolute -bottom-32 -left-24 w-[320px] h-[320px] rounded-full bg-[#F2C9C9] opacity-90 pointer-events-none" />

			<div className="flex flex-col items-center justify-center min-h-screen px-4 py-8 relative z-10">
				{/* Main Content Container */}
				<div className="w-full max-w-[980px] flex flex-col md:flex-row items-center justify-center gap-8 md:gap-12">
					{/* Left Side - Branding */}
					<div className="flex flex-col items-center md:items-start text-center md:text-left mb-8 md:mb-0">
						<div className="mb-4">
							<h1 className="text-[#E67A2E] text-5xl md:text-6xl font-bold mb-2">
								Learn & Earn
							</h1>
						</div>
						<p className="text-black text-xl md:text-2xl font-semibold">
							Learn And Earn With Our App
						</p>
					</div>

					{/* Right Side - Login/Sign Up Form */}
					<div className="w-full max-w-[396px]">
						<form
							onSubmit={handleSubmit}
							className="bg-white rounded-lg shadow-md p-4 md:p-6"
							style={{
								boxShadow: "0px 2px 8px rgba(0, 0, 0, 0.1)"
							}}
						>
							{/* Login/Sign Up Toggle */}
							<div className="flex justify-around mb-4 pb-2 border-b border-gray-300">
								<button
									type="button"
									onClick={() => setIsLogin(true)}
									className={`text-xl font-bold px-4 py-2 rounded transition-colors ${
										isLogin
											? "text-white bg-[#E67A2E]"
											: "text-gray-600 bg-transparent hover:text-[#E67A2E]"
									}`}
								>
									Login
								</button>
								<button
									type="button"
									onClick={() => setIsLogin(false)}
									className={`text-xl font-bold px-4 py-2 rounded transition-colors ${
										!isLogin
											? "text-white bg-[#E67A2E]"
											: "text-gray-600 bg-transparent hover:text-[#E67A2E]"
									}`}
								>
									Sign Up
								</button>
							</div>

							{/* Form Header */}
							<div className="mb-6">
								<h2 className="text-2xl font-semibold text-gray-900 mb-1">
									{isLogin ? "Log in to Learn & Earn" : "Create a new account"}
								</h2>
								{!isLogin && (
									<p className="text-sm text-gray-600">Quick and easy.</p>
								)}
							</div>

							{/* Name (Sign Up only) */}
							{!isLogin && (
								<div className="grid grid-cols-2 gap-3 mb-4">
									<input
										type="text"
										placeholder="Name"
										value={firstName}
										onChange={(e) => setFirstName(e.target.value)}
										className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#E67A2E] focus:border-transparent"
										required
									/>
									<input
										type="text"
										placeholder="Surname"
										value={lastName}
										onChange={(e) => setLastName(e.target.value)}
										className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#E67A2E] focus:border-transparent"
										required
									/>
								</div>
							)}

							{/* Birthday (Sign Up only) */}
							{!isLogin && (
								<div className="mb-4">
									<label className="block text-xs text-gray-600 mb-1">D.O.B</label>
									<div className="grid grid-cols-3 gap-2">
										<select className="w-full px-2 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#E67A2E] focus:border-transparent" defaultValue="1">
											{Array.from({ length: 31 }, (_, i) => i + 1).map((d) => (
												<option key={d} value={d}>{d}</option>
											))}
										</select>
										<select className="w-full px-2 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#E67A2E] focus:border-transparent" defaultValue="January">
											{["January","February","March","April","May","June","July","August","September","October","November","December"].map((m) => (
												<option key={m} value={m}>{m}</option>
											))}
										</select>
										<select className="w-full px-2 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#E67A2E] focus:border-transparent" defaultValue="2025">
											{Array.from({ length: 80 }, (_, i) => 2025 - i).map((y) => (
												<option key={y} value={y}>{y}</option>
											))}
										</select>
									</div>
								</div>
							)}

							{/* Gender (Sign Up only) */}
							{!isLogin && (
								<div className="mb-4">
									<label className="block text-xs text-gray-600 mb-1">Gender</label>
									<div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
										<label className="flex items-center justify-between px-3 py-2 border border-gray-300 rounded-md text-sm">
											<span>Female</span>
											<input type="radio" name="gender" className="h-4 w-4" checked={gender === "Female"} onChange={() => setGender("Female")} />
										</label>
										<label className="flex items-center justify-between px-3 py-2 border border-gray-300 rounded-md text-sm">
											<span>Male</span>
											<input type="radio" name="gender" className="h-4 w-4" checked={gender === "Male"} onChange={() => setGender("Male")} />
										</label>
										<label className="flex items-center justify-between px-3 py-2 border border-gray-300 rounded-md text-sm">
											<span>Others</span>
											<input type="radio" name="gender" className="h-4 w-4" checked={gender === "Other"} onChange={() => setGender("Other")} />
										</label>
										<label className="flex items-center justify-between px-3 py-2 border border-gray-300 rounded-md text-sm">
											<span>Prefer not to say</span>
											<input type="radio" name="gender" className="h-4 w-4" checked={gender === "Prefer not to say"} onChange={() => setGender("Prefer not to say")} />
										</label>
									</div>
								</div>
							)}

							{/* Email/Phone Input */}
							<div className="mb-4">
								<label className="block text-sm font-semibold text-gray-800 mb-1">
									Email or Phone Number <span className="text-red-500">*</span>
								</label>
								<div className="relative">
									<input
										type="text"
										value={emailOrPhone}
										onChange={(e) => setEmailOrPhone(e.target.value)}
										placeholder="Email address"
										className="w-full px-4 py-3 border border-gray-300 rounded-md text-base focus:outline-none focus:ring-2 focus:ring-[#E67A2E] focus:border-transparent pr-12"
										required
										autoFocus
									/>
									{emailOrPhone ? (
										<div
											className={`absolute right-3 top-1/2 -translate-y-1/2 h-7 w-7 rounded-full flex items-center justify-center text-base font-bold ${
												emailValid ? "bg-green-500/80 text-white" : "bg-red-500/80 text-white"
											}`}
										>
											{emailValid ? "✓" : "✕"}
										</div>
									) : null}
								</div>
								{!isLogin && (
									<div className="mt-3 flex items-start gap-2">
									<div className="flex-1">
										<label className="block text-xs text-gray-600 mb-1">Email OTP</label>
										<div className="relative">
											<input
												type="text"
												value={emailOtp}
												onChange={(e) => setEmailOtp(e.target.value)}
												placeholder="Enter 6-digit OTP"
												className="w-full px-4 py-3 border border-gray-300 rounded-md text-base focus:outline-none focus:ring-2 focus:ring-[#E67A2E] focus:border-transparent pr-12"
											/>
											{emailOtp ? (
												<div
													className={`absolute right-3 top-1/2 -translate-y-1/2 h-7 w-7 rounded-full flex items-center justify-center text-base font-bold ${
														emailOtpStatus === "verified"
															? "bg-green-500/50 text-white"
															: emailOtpValid
															? "bg-red-500/50 text-white"
															: "bg-red-500/50 text-white"
													}`}
												>
													{emailOtpStatus === "verified" ? "✓" : "✕"}
												</div>
											) : null}
										</div>
									</div>
									<div className="flex flex-col items-end gap-2">
										<button
											type="button"
											onClick={handleSendEmailOtp}
											className="px-4 py-2 bg-[#E67A2E] text-white rounded-md font-semibold hover:bg-[#d66a1e]"
										>
											Send
										</button>
										<button
											type="button"
											onClick={handleVerifyEmailOtp}
											className="px-4 py-2 bg-gray-800 text-white rounded-md font-semibold hover:bg-gray-700"
											disabled={!emailOtpValid || emailOtpStatus === "verifying"}
										>
											{emailOtpStatus === "verifying" ? "Verifying..." : "Verify"}
										</button>
									</div>
								</div>
								)}
							</div>

							{/* Phone (Sign Up only) */}
							{!isLogin && (
								<div className="mb-4">
									<label className="block text-sm font-semibold text-gray-800 mb-1">
										Phone Number <span className="text-red-500">*</span>
									</label>
									<div className="relative flex items-center">
										<span className="px-3 py-3 border border-gray-300 rounded-l-md bg-gray-50 text-sm text-gray-700 select-none">
											+91
										</span>
										<input
											type="tel"
											value={phoneNumber}
											onChange={(e) => setPhoneNumber(e.target.value)}
											placeholder="10-digit number"
											className="w-full px-4 py-3 border border-gray-300 rounded-r-md text-base focus:outline-none focus:ring-2 focus:ring-[#E67A2E] focus:border-transparent pr-12"
											required
										/>
										{phoneNumber ? (
											<div
												className={`absolute right-3 top-1/2 -translate-y-1/2 h-7 w-7 rounded-full flex items-center justify-center text-base font-bold ${
													phoneValid ? "bg-green-500/80 text-white" : "bg-red-500/80 text-white"
												}`}
											>
												{phoneValid ? "✓" : "✕"}
											</div>
										) : null}
									</div>
									<div className="mt-3 flex items-start gap-2">
										<div className="flex-1">
											<label className="block text-xs text-gray-600 mb-1">Phone OTP</label>
											<div className="relative">
												<input
													type="text"
													value={phoneOtp}
													onChange={(e) => setPhoneOtp(e.target.value)}
													placeholder="Enter 6-digit OTP"
													className="w-full px-4 py-3 border border-gray-300 rounded-md text-base focus:outline-none focus:ring-2 focus:ring-[#E67A2E] focus:border-transparent pr-12"
												/>
												{phoneOtp ? (
													<div
														className={`absolute right-3 top-1/2 -translate-y-1/2 h-7 w-7 rounded-full flex items-center justify-center text-base font-bold ${
															phoneOtpStatus === "verified"
																? "bg-green-500/50 text-white"
																: phoneOtpValid
																? "bg-red-500/50 text-white"
																: "bg-red-500/50 text-white"
														}`}
													>
														{phoneOtpStatus === "verified" ? "✓" : "✕"}
													</div>
												) : null}
											</div>
										</div>
										<div className="flex flex-col items-end gap-2">
											<button
												type="button"
												onClick={handleSendPhoneOtp}
												className="px-4 py-2 bg-[#E67A2E] text-white rounded-md font-semibold hover:bg-[#d66a1e]"
											>
												Send
											</button>
											<button
												type="button"
												onClick={handleVerifyPhoneOtp}
												className="px-4 py-2 bg-gray-800 text-white rounded-md font-semibold hover:bg-gray-700"
												disabled={!phoneOtpValid || phoneOtpStatus === "verifying"}
											>
												{phoneOtpStatus === "verifying" ? "Verifying..." : "Verify"}
											</button>
										</div>
									</div>
								</div>
							)}

							{/* Password Input */}
							<div className="mb-4">
								<label className="block text-sm font-semibold text-gray-800 mb-1">
									{isLogin ? "Password" : "Password"} <span className="text-red-500">*</span>
								</label>
								<div className="flex gap-2">
									<div className="relative flex-1">
										<input
											type={showPassword ? "text" : "password"}
											value={password}
											onChange={(e) => setPassword(e.target.value)}
											placeholder={isLogin ? "Password" : "New Password"}
											className="w-full px-4 py-3 border border-gray-300 rounded-l-md text-base focus:outline-none focus:ring-2 focus:ring-[#E67A2E] focus:border-transparent pr-12"
											required
										/>
										<button
											type="button"
											onClick={() => setShowPassword(!showPassword)}
											className="absolute right-3 top-1/2 transform -translate-y-1/2 text-sm text-gray-600 hover:text-[#E67A2E] font-medium"
										>
											{showPassword ? "Hide" : "Show"}
										</button>
									</div>
									{!isLogin && (
										<button
											type="button"
											onClick={generatePassword}
											className="px-4 py-3 bg-[#E67A2E] text-white rounded-r-md font-semibold hover:bg-[#d66a1e] text-sm whitespace-nowrap"
										>
											++ Suggest
										</button>
									)}
								</div>
							</div>

							{/* Confirm Password (Sign Up only) */}
							{!isLogin && (
								<div className="mb-4 relative">
									<label className="block text-sm font-semibold text-gray-800 mb-1">
										Confirm Password <span className="text-red-500">*</span>
									</label>
									<input
										type={showConfirmPassword ? "text" : "password"}
										value={confirmPassword}
										onChange={(e) => setConfirmPassword(e.target.value)}
										placeholder="Confirm new password"
										className="w-full px-4 py-3 border border-gray-300 rounded-md text-base focus:outline-none focus:ring-2 focus:ring-[#E67A2E] focus:border-transparent pr-12"
										required
									/>
									<button
										type="button"
										onClick={() => setShowConfirmPassword(!showConfirmPassword)}
										className="absolute right-3 top-1/2 transform -translate-y-1/2 text-sm text-gray-600 hover:text-[#E67A2E] font-medium"
									>
										{showConfirmPassword ? "Hide" : "Show"}
									</button>
								</div>
							)}

							{/* Status messages */}
							{message && (
								<div className="mb-3 text-green-700 text-sm font-semibold">
									{message}
								</div>
							)}
							{error && (
								<div className="mb-3 text-red-600 text-sm font-semibold">
									{error}
								</div>
							)}

							{/* Submit Button */}
							<button
								type="submit"
								disabled={loading}
								className={`w-full text-white font-semibold py-3 rounded-md text-lg transition-colors mb-4 ${
									isLogin ? "bg-[#E53935] hover:bg-[#c62828]" : "bg-[#E53935] hover:bg-[#c62828]"
								} ${loading ? "opacity-80 cursor-not-allowed" : ""}`}
							>
								{loading ? "Please wait..." : isLogin ? "Log In" : "Create Account"}
							</button>

							{/* Google Sign In (Login only) */}
							{isLogin && (
								<div className="mb-4">
									<div className="text-center text-sm text-gray-600 mb-2">Continue with Google</div>
									<div 
										id="google-signin-button"
										className="w-full"
									></div>
									{googleLoading && (
										<div className="text-center text-sm text-gray-600 mt-2">Signing in with Google...</div>
									)}
								</div>
							)}

							{/* Agreements (Sign Up only) */}
							{!isLogin && (
								<div className="space-y-3 mb-4 text-sm text-gray-800">
									<label className="flex items-start gap-2">
										<input type="checkbox" className="mt-1 h-4 w-4 accent-[#F5A623]" />
										<span>
											I accept the{" "}
											<span className="text-black/50 font-semibold">Terms & Conditions</span> and{" "}
											<span className="text-black/50 font-semibold">Privacy Policy</span>
										</span>
									</label>
									<label className="flex items-start gap-2">
										<input type="checkbox" className="mt-1 h-4 w-4 accent-[#F5A623]" />
										<span className="flex flex-col gap-1">
											I accept the Data & Contacts Authorization
											<a href="#" className="text-[#F5A623] font-semibold flex items-center gap-1">
												<span className="text-sm">ⓘ</span> View Details &gt;
											</a>
										</span>
									</label>
									<label className="flex items-start gap-2">
										<input type="checkbox" className="mt-1 h-4 w-4 accent-[#F5A623]" />
										<span className="text-[#F5A623] font-medium">
											I understand my entire online public profile will be scanned for giving weightage
										</span>
									</label>
								</div>
							)}

							{/* Forgot Password Link (only in Login mode) */}
							{isLogin && (
								<div className="text-center text-sm text-gray-600 border-t pt-4 space-y-2">
									<a
										href="#"
										onClick={(e) => {
											e.preventDefault();
											handleForgotPassword();
										}}
										className="text-[#E67A2E] hover:underline block"
									>
										Forgotten account?
									</a>
									<div className="text-gray-700">
										Don't have an account?{" "}
										<button
											type="button"
											onClick={() => setIsLogin(false)}
											className="text-[#F5A623] font-semibold hover:underline"
										>
											Sign Up
										</button>
									</div>
								</div>
							)}
						</form>
					</div>
				</div>

				{/* Footer */}
				<div className="mt-10 w-full max-w-[980px] text-center text-sm text-gray-600">
					<div className="flex items-center gap-3 text-gray-500 text-[12px] mb-3">
						<hr className="flex-1 border-t border-gray-400/30" />
						<div className="flex flex-wrap justify-center gap-4">
							<span>Earn</span>
							<span>Fun</span>
							<span>Meals</span>
							<span>Shop</span>
							<span>E-journals</span>
							<span>Friends & Family</span>
							<span>Chat</span>
							<span>And</span>
							<span>Earn more…</span>
						</div>
						<hr className="flex-1 border-t border-gray-400/30" />
					</div>
					<div className="flex flex-wrap justify-center items-center gap-3 mb-4 text-gray-500 text-[12px]">
						<span>English (US)</span>
						<span>English (UK)</span>
						<span>Spanish (Espanol)</span>
						<span>Brazilian Portuguese</span>
						<span>French</span>
						<span>हिन्दी</span>
						<span>Italian</span>
						<span>German</span>
						<span>Turkish</span>
						<span>Indonesian</span>
						<span>Arabic</span>
						<button
							type="button"
							className="px-2 py-1 border border-gray-300 rounded hover:bg-gray-100"
							aria-label="More languages"
						>
							+
						</button>
					</div>
					<div className="text-gray-500">
						Learn & Earn © 2025
					</div>
				</div>
			</div>

			{/* Forgot Password Modal */}
			{forgotOpen && (
				<div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/60 px-4">
					<div className="w-full max-w-md bg-[#252525] text-white rounded-t-2xl md:rounded-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
						<div className="w-12 h-1.5 bg-white/30 rounded-full mx-auto mb-6"></div>
						
						{forgotStep === "send" && (
							<>
								<h2 className="text-2xl font-semibold mb-1">Forgot Password</h2>
								<p className="text-sm text-gray-300 mb-4">
									Enter your {forgotMode === "email" ? "email" : "phone number"} to receive OTP
								</p>

								<div className="flex items-center gap-3 mb-4">
									<button
										className={`flex-1 py-2 rounded-lg font-semibold ${
											forgotMode === "email" ? "bg-[#E67A2E] text-white" : "bg-white/10 text-gray-200"
										}`}
										onClick={() => {
											setForgotMode("email");
											setForgotValue("");
											setForgotMessage("");
											setError("");
										}}
									>
										Email
									</button>
									<button
										className={`flex-1 py-2 rounded-lg font-semibold ${
											forgotMode === "phone" ? "bg-[#E67A2E] text-white" : "bg-white/10 text-gray-200"
										}`}
										onClick={() => {
											setForgotMode("phone");
											setForgotValue("");
											setForgotMessage("");
											setError("");
										}}
									>
										Phone
									</button>
								</div>

								<div className="mb-4">
									<label className="block text-sm text-gray-300 mb-1">
										{forgotMode === "email" ? "Email ID" : "Phone Number"}
									</label>
									<input
										type={forgotMode === "email" ? "email" : "tel"}
										value={forgotValue}
										onChange={(e) => setForgotValue(e.target.value)}
										placeholder={forgotMode === "email" ? "Enter your Email ID" : "Enter 10-digit phone"}
										className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#E67A2E]"
									/>
								</div>

								{forgotMessage && <div className="text-sm text-green-400 mb-2">{forgotMessage}</div>}
								{error && <div className="text-sm text-red-400 mb-2">{error}</div>}

								<div className="flex items-center justify-between text-sm text-[#E67A2E] font-semibold mb-4">
									<button
										type="button"
										onClick={() => setForgotMode(forgotMode === "email" ? "phone" : "email")}
										className="hover:underline"
									>
										Use {forgotMode === "email" ? "Phone Number" : "Email"} Instead
									</button>
								</div>

								<div className="space-y-3">
									<button
										type="button"
										onClick={handleForgotSubmit}
										disabled={forgotLoading}
										className="w-full bg-[#E67A2E] text-white font-semibold py-3 rounded-xl hover:bg-[#d66a1e] disabled:opacity-60"
									>
										{forgotLoading ? "Sending..." : "Send OTP"}
									</button>
									<button
										type="button"
										onClick={() => setForgotOpen(false)}
										className="w-full bg-white/10 text-white font-semibold py-3 rounded-xl hover:bg-white/20"
									>
										Close
									</button>
								</div>
							</>
						)}

						{forgotStep === "verify" && (
							<>
								<h2 className="text-2xl font-semibold mb-1">Forgot Password</h2>
								<p className="text-sm text-gray-300 mb-4">
									Enter the OTP sent to your {forgotMode === "email" ? "email" : "phone"}
								</p>

								{/* 6-digit OTP Input */}
								<div className="mb-4">
									<div className="flex gap-2 justify-center">
										{forgotOtp.map((digit, index) => (
											<input
												key={index}
												id={`forgot-otp-${index}`}
												type="text"
												maxLength={1}
												value={digit}
												onChange={(e) => handleForgotOtpChange(index, e.target.value)}
												onKeyDown={(e) => handleForgotOtpKeyDown(index, e)}
												className={`w-12 h-12 text-center text-xl font-bold rounded-lg border-2 ${
													index === forgotOtpIndex
														? "border-[#E67A2E] bg-white/10"
														: "border-white/20 bg-white/5"
												} text-white focus:outline-none focus:ring-2 focus:ring-[#E67A2E]`}
												autoFocus={index === 0}
											/>
										))}
									</div>
									{resendTimer > 0 ? (
										<p className="text-sm text-gray-400 text-center mt-3">
											Resend OTP in {resendTimer}s
										</p>
									) : (
										<button
											type="button"
											onClick={handleForgotSubmit}
											className="text-sm text-[#E67A2E] font-semibold mx-auto block mt-3 hover:underline"
										>
											Resend OTP
										</button>
									)}
								</div>

								{error && <div className="text-sm text-red-400 mb-2">{error}</div>}

								<button
									type="button"
									onClick={handleVerifyForgotOtp}
									disabled={forgotLoading || forgotOtp.join("").length !== 6}
									className="w-full bg-[#E67A2E] text-white font-semibold py-3 rounded-xl hover:bg-[#d66a1e] disabled:opacity-60 mb-3"
								>
									{forgotLoading ? "Verifying..." : "Verify OTP"}
								</button>
								<button
									type="button"
									onClick={() => setForgotStep("send")}
									className="w-full bg-white/10 text-white font-semibold py-3 rounded-xl hover:bg-white/20"
								>
									Back
								</button>
							</>
						)}

						{forgotStep === "reset" && (
							<>
								<h2 className="text-2xl font-semibold mb-1">Reset Password</h2>
								<p className="text-sm text-gray-300 mb-4">
									Enter your new password
								</p>

								<div className="mb-4">
									<label className="block text-sm font-semibold text-white mb-1">
										New Password
									</label>
									<div className="relative">
										<input
											type={showNewPassword ? "text" : "password"}
											value={newPassword}
											onChange={(e) => setNewPassword(e.target.value)}
											placeholder="Enter new password"
											className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#E67A2E] pr-12"
										/>
										<button
											type="button"
											onClick={() => setShowNewPassword(!showNewPassword)}
											className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400"
										>
											{showNewPassword ? "👁️" : "👁️‍🗨️"}
										</button>
									</div>
								</div>

								<div className="mb-4">
									<label className="block text-sm font-semibold text-white mb-1">
										Confirm Password
									</label>
									<div className="relative">
										<input
											type={showConfirmPassword ? "text" : "password"}
											value={confirmPassword}
											onChange={(e) => setConfirmPassword(e.target.value)}
											placeholder="Confirm new password"
											className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#E67A2E] pr-12"
										/>
										<button
											type="button"
											onClick={() => setShowConfirmPassword(!showConfirmPassword)}
											className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400"
										>
											{showConfirmPassword ? "👁️" : "👁️‍🗨️"}
										</button>
									</div>
								</div>

								{forgotMessage && <div className="text-sm text-green-400 mb-2">{forgotMessage}</div>}
								{error && <div className="text-sm text-red-400 mb-2">{error}</div>}

								<button
									type="button"
									onClick={handleResetPassword}
									disabled={forgotLoading}
									className="w-full bg-[#E53935] text-white font-semibold py-3 rounded-xl hover:bg-[#c62828] disabled:opacity-60 mb-3"
								>
									{forgotLoading ? "Resetting..." : "Reset Password"}
								</button>
								<button
									type="button"
									onClick={() => setForgotStep("verify")}
									className="w-full bg-white/10 text-white font-semibold py-3 rounded-xl hover:bg-white/20"
								>
									Back
								</button>
							</>
						)}
					</div>
				</div>
			)}
		</div>
	);
}

