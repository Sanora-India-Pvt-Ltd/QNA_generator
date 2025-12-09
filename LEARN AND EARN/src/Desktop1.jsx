import React, { useState, useEffect } from "react";

export default function Desktop1(props) {
	const [searchQuery, setSearchQuery] = useState("");
	const [activeMenuItem, setActiveMenuItem] = useState("My Weightage");
	const [showProfileDropdown, setShowProfileDropdown] = useState(false);
	const [showNotifications, setShowNotifications] = useState(false);
	const [imageErrors, setImageErrors] = useState({});
	const [notifications, setNotifications] = useState([
		{ id: 1, message: "Welcome to Learn & Earn!", time: "2 hours ago", read: false }
	]);

	const menuItems = [
		{ id: "My Weightage", icon: "https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/3igess1f_expires_30_days.png", indicator: "https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/p5oelfj0_expires_30_days.png" },
		{ id: "Tasty Meals", icon: "https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/bzrs61kx_expires_30_days.png" },
		{ id: "Course", icon: "https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/znmjhxqu_expires_30_days.png" },
		{ id: "Friends & Family", icon: "https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/8bh7ft2c_expires_30_days.png" },
		{ id: "Fun Reels", icon: "https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/b60e7een_expires_30_days.png" },
		{ id: "Shop & Earn", icon: "https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/b4cp3ya0_expires_30_days.png" },
		{ id: "Withdraw Permissions", icon: "https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/fwsbyae2_expires_30_days.png" },
		{ id: "Live Journals & Conferences", icon: "https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/dmxo63gf_expires_30_days.png" },
		{ id: "Read More", icon: "https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/ai2mfb83_expires_30_days.png" }
	];

	const handleSearch = (e) => {
		e.preventDefault();
		if (searchQuery.trim()) {
			console.log("Searching for:", searchQuery);
			alert(`Searching for: ${searchQuery}`);
		}
	};

	const handleMenuItemClick = (itemId) => {
		setActiveMenuItem(itemId);
		console.log("Selected menu item:", itemId);
	};

	const handleLogout = () => {
		localStorage.removeItem("accessToken");
		localStorage.removeItem("refreshToken");
		window.location.reload();
	};

	const handleNotificationClick = () => {
		setShowNotifications(!showNotifications);
		// Mark notifications as read when opened
		if (!showNotifications) {
			setNotifications(prev => prev.map(n => ({ ...n, read: true })));
		}
	};

	const handleImageError = (imageId) => {
		setImageErrors(prev => ({ ...prev, [imageId]: true }));
	};

	const handleMenuAction = (menuId) => {
		setActiveMenuItem(menuId);
		// You can add navigation or content change logic here
		console.log(`Navigating to: ${menuId}`);
		// Example: Could trigger content change, API call, etc.
	};

	const handleIconClick = (iconName) => {
		console.log(`${iconName} clicked`);
		// Add specific functionality for each icon
		switch(iconName) {
			case "Icon 1":
				// Add functionality for Icon 1
				break;
			case "Icon 2":
				// Add functionality for Icon 2
				break;
			case "Icon 3":
				// Add functionality for Icon 3
				break;
			default:
				break;
		}
	};

	const handleMenuButtonClick = (menuIndex) => {
		console.log(`Menu button ${menuIndex + 1} clicked`);
		// Add navigation or action logic here
	};

	// Close dropdowns when clicking outside
	useEffect(() => {
		const handleClickOutside = (event) => {
			if (showProfileDropdown || showNotifications) {
				const target = event.target;
				if (!target.closest('.profile-dropdown') && !target.closest('.profile-button')) {
					setShowProfileDropdown(false);
				}
				if (!target.closest('.notification-dropdown') && !target.closest('.notification-button')) {
					setShowNotifications(false);
				}
			}
		};

		document.addEventListener('mousedown', handleClickOutside);
		return () => {
			document.removeEventListener('mousedown', handleClickOutside);
		};
	}, [showProfileDropdown, showNotifications]);

	return (
		<div className="items-start bg-white min-h-screen">
			<div className="flex flex-col items-start bg-[#F0F2F5] w-full max-w-[1440px] mx-auto pb-[1px]">
				{/* Header */}
				<div className="flex items-start self-stretch bg-white py-[7px] w-full">
					{/* Search Bar */}
					<div className="w-[355px] px-4 ml-[49px]">
						<div className="flex flex-col items-end self-stretch relative py-2">
							<form onSubmit={handleSearch} className="w-full">
								<div className="flex items-center bg-[#F0F2F5] rounded-[50px] w-full hover:bg-[#E4E6E9] transition-colors focus-within:bg-[#E4E6E9] focus-within:ring-2 focus-within:ring-[#E67A2E]/20">
									<button 
										type="submit" 
										className="p-2 hover:opacity-80 transition-opacity cursor-pointer"
										aria-label="Search"
									>
										{imageErrors.searchIcon ? (
											<svg className="w-7 h-7 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
											</svg>
										) : (
											<img
												src={"https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/ugiyufad_expires_30_days.png"} 
												className="w-7 h-10 rounded-[50px] object-fill"
												alt="Search"
												onError={() => handleImageError('searchIcon')}
											/>
										)}
									</button>
									<input
										type="text"
										value={searchQuery}
										onChange={(e) => setSearchQuery(e.target.value)}
										placeholder="Search..."
										className="flex-1 h-10 py-2.5 px-2 rounded-[50px] bg-transparent outline-none text-sm text-gray-700 placeholder-gray-400"
									/>
								</div>
							</form>
							<button
								onClick={() => window.location.reload()}
								className="absolute top-[18px] left-0 cursor-pointer hover:opacity-80 transition-opacity"
								aria-label="Home"
							>
								{imageErrors.logo ? (
									<span className="text-[#E67A2E] text-lg font-bold">LE</span>
								) : (
									<img
										src={"https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/u0p7s30p_expires_30_days.png"} 
										className="w-[60px] h-5 object-fill"
										alt="Logo"
										onError={() => handleImageError('logo')}
									/>
								)}
							</button>
						</div>
					</div>
					
					<div className="flex-1 self-stretch"></div>
					
					{/* Center Menu */}
					<div className="flex flex-col items-start w-[676px]">
						<div className="flex items-start bg-white px-[5px]">
							<button 
								className="w-[111px] h-[53px] hover:opacity-80 active:scale-95 transition-all cursor-pointer rounded"
								onClick={() => handleMenuButtonClick(0)}
								aria-label="Menu 1"
							>
								{imageErrors.menu1 ? (
									<div className="w-full h-full bg-gray-200 rounded flex items-center justify-center text-xs">Menu 1</div>
								) : (
									<img
										src={"https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/doy4k8kb_expires_30_days.png"} 
										className="w-[111px] h-[53px] object-fill"
										alt="Menu 1"
										onError={() => handleImageError('menu1')}
									/>
								)}
							</button>
							<button 
								className="w-[119px] h-[53px] hover:opacity-80 active:scale-95 transition-all cursor-pointer rounded"
								onClick={() => handleMenuButtonClick(1)}
								aria-label="Menu 2"
							>
								{imageErrors.menu2 ? (
									<div className="w-full h-full bg-gray-200 rounded flex items-center justify-center text-xs">Menu 2</div>
								) : (
									<img
										src={"https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/sia9ebs0_expires_30_days.png"} 
										className="w-[119px] h-[53px] object-fill"
										alt="Menu 2"
										onError={() => handleImageError('menu2')}
									/>
								)}
							</button>
							<button 
								className="w-[119px] h-[53px] hover:opacity-80 active:scale-95 transition-all cursor-pointer rounded"
								onClick={() => handleMenuButtonClick(2)}
								aria-label="Menu 3"
							>
								{imageErrors.menu3 ? (
									<div className="w-full h-full bg-gray-200 rounded flex items-center justify-center text-xs">Menu 3</div>
								) : (
									<img
										src={"https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/nna9qepb_expires_30_days.png"} 
										className="w-[119px] h-[53px] object-fill"
										alt="Menu 3"
										onError={() => handleImageError('menu3')}
									/>
								)}
							</button>
						</div>
						<div className="flex flex-col items-end self-stretch">
							<div className="flex items-start bg-white py-[15px]">
								<button 
									className="w-[26px] h-[26px] ml-[43px] mr-[74px] hover:opacity-80 active:scale-90 transition-all cursor-pointer"
									onClick={() => handleIconClick("Icon 1")}
									title="Icon 1"
									aria-label="Icon 1"
								>
									{imageErrors.icon1 ? (
										<div className="w-full h-full bg-gray-300 rounded"></div>
									) : (
										<img
											src={"https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/ka7jna4i_expires_30_days.png"} 
											className="w-[26px] h-[26px] object-fill"
											alt="Icon 1"
											onError={() => handleImageError('icon1')}
										/>
									)}
								</button>
								<button 
									className="w-[26px] h-[26px] mr-[74px] hover:opacity-80 active:scale-90 transition-all cursor-pointer"
									onClick={() => handleIconClick("Icon 2")}
									title="Icon 2"
									aria-label="Icon 2"
								>
									{imageErrors.icon2 ? (
										<div className="w-full h-full bg-gray-300 rounded"></div>
									) : (
										<img
											src={"https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/8mg28vm3_expires_30_days.png"} 
											className="w-[26px] h-[26px] object-fill"
											alt="Icon 2"
											onError={() => handleImageError('icon2')}
										/>
									)}
								</button>
								<button 
									className="w-[26px] h-[26px] mr-[58px] hover:opacity-80 active:scale-90 transition-all cursor-pointer"
									onClick={() => handleIconClick("Icon 3")}
									title="Icon 3"
									aria-label="Icon 3"
								>
									{imageErrors.icon3 ? (
										<div className="w-full h-full bg-gray-300 rounded"></div>
									) : (
										<img
											src={"https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/n03gjn71_expires_30_days.png"} 
											className="w-[26px] h-[26px] object-fill"
											alt="Icon 3"
											onError={() => handleImageError('icon3')}
										/>
									)}
								</button>
							</div>
						</div>
					</div>
					
					<div className="flex-1 self-stretch"></div>
					
					{/* Notifications */}
					<div className="relative">
						<button
							onClick={handleNotificationClick}
							className="notification-button w-6 h-6 mr-[18px] hover:opacity-80 active:scale-90 transition-all cursor-pointer relative"
							title="Notifications"
							aria-label="Notifications"
						>
							{imageErrors.notification ? (
								<svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
								</svg>
							) : (
								<img
									src={"https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/z0yantmf_expires_30_days.png"} 
									className="w-6 h-6 object-fill"
									alt="Notification"
									onError={() => handleImageError('notification')}
								/>
							)}
							{/* Notification badge */}
							{notifications.filter(n => !n.read).length > 0 && (
								<span className="absolute -top-1 -right-2 w-3 h-3 bg-red-500 rounded-full border-2 border-white animate-pulse"></span>
							)}
						</button>
						{showNotifications && (
							<div className="notification-dropdown absolute right-0 top-8 w-64 bg-white rounded-lg shadow-lg border border-gray-200 p-4 z-50 max-h-96 overflow-y-auto">
								<div className="text-sm font-semibold mb-3 text-gray-800">Notifications</div>
								{notifications.length === 0 ? (
									<div className="text-xs text-gray-500">No new notifications</div>
								) : (
									<div className="space-y-2">
										{notifications.map((notification) => (
											<div 
												key={notification.id} 
												className={`p-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${!notification.read ? 'bg-blue-50' : ''}`}
											>
												<div className="text-xs text-gray-800">{notification.message}</div>
												<div className="text-xs text-gray-500 mt-1">{notification.time}</div>
											</div>
										))}
									</div>
								)}
							</div>
						)}
					</div>
					
					{/* Profile */}
					<div className="relative flex flex-col items-center w-[84px] mr-[15px] gap-[11px]">
						<button
							onClick={() => window.location.reload()}
							className="text-[#E67A2E] text-[15px] font-bold cursor-pointer hover:opacity-80 active:scale-95 transition-all"
							aria-label="Learn & Earn Home"
						>
							{"Learn & Earn"}
						</button>
						<button
							onClick={() => setShowProfileDropdown(!showProfileDropdown)}
							className="profile-button relative cursor-pointer hover:opacity-80 active:scale-95 transition-all"
							title="Profile"
							aria-label="Profile Menu"
						>
							{imageErrors.profile ? (
								<div className="w-[38px] h-[38px] bg-[#E67A2E] rounded-full flex items-center justify-center text-white font-bold">
									U
								</div>
							) : (
								<img
									src={"https://storage.googleapis.com/tagjs-prod.appspot.com/v1/vXrD2L2AXC/ntcuv2kn_expires_30_days.png"} 
									className="w-[38px] h-[38px] object-fill rounded-full border-2 border-[#E67A2E]"
									alt="Profile"
									onError={() => handleImageError('profile')}
								/>
							)}
						</button>
						{showProfileDropdown && (
							<div className="profile-dropdown absolute right-0 top-16 w-48 bg-white rounded-lg shadow-lg border border-gray-200 p-2 z-50">
								<button
									onClick={() => {
										console.log("Profile clicked");
										setShowProfileDropdown(false);
									}}
									className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded transition-colors flex items-center gap-2"
								>
									<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
									</svg>
									View Profile
								</button>
								<button
									onClick={() => {
										console.log("Settings clicked");
										setShowProfileDropdown(false);
									}}
									className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded transition-colors flex items-center gap-2"
								>
									<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
										<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
									</svg>
									Settings
								</button>
								<hr className="my-1" />
								<button
									onClick={handleLogout}
									className="w-full text-left px-3 py-2 text-sm hover:bg-red-50 text-red-600 rounded transition-colors flex items-center gap-2"
								>
									<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
									</svg>
									Logout
								</button>
							</div>
						)}
					</div>
				</div>
				{/* Sidebar Menu */}
				<div className="flex flex-col items-start bg-white w-full">
					<div className="flex flex-col items-start bg-white w-full">
						{menuItems.map((item, index) => {
							const isActive = activeMenuItem === item.id;
							const marginBottom = index === 2 ? "mb-[50px]" : index === menuItems.length - 1 ? "mb-[81px]" : "mb-[60px]";
							const marginRight = index === 7 ? "mr-[22px]" : "";
							const gap = index === 0 ? "gap-[19px]" : index === menuItems.length - 1 ? "gap-4" : "gap-[18px]";
							
							return (
								<button
									key={item.id}
									onClick={() => {
										handleMenuItemClick(item.id);
										handleMenuAction(item.id);
									}}
									className={`flex items-center ${marginBottom} ml-[50px] ${marginRight} ${gap} w-full hover:bg-gray-50 active:bg-gray-100 transition-all rounded-lg px-2 py-1 group cursor-pointer ${
										isActive ? 'bg-gray-50' : ''
									}`}
									aria-label={item.id}
									aria-current={isActive ? 'page' : undefined}
								>
									<div className="flex flex-col items-start w-[39px] relative">
										{imageErrors[`menu-icon-${index}`] ? (
											<div className={`w-[39px] h-10 bg-gray-200 rounded flex items-center justify-center text-xs ${isActive ? 'bg-[#E67A2E]/20' : ''}`}>
												{item.id.charAt(0)}
											</div>
										) : (
											<img
												src={item.icon}
												className={`w-[39px] h-10 object-fill transition-opacity ${isActive ? 'opacity-100' : 'opacity-70 group-hover:opacity-100'}`}
												alt={item.id}
												onError={() => handleImageError(`menu-icon-${index}`)}
											/>
										)}
										{isActive && item.indicator && !imageErrors[`menu-indicator-${index}`] && (
											<img
												src={item.indicator}
												className="self-stretch h-[26px] absolute bottom-[-1px] right-1.5 left-1.5 object-fill"
												alt="Indicator"
												onError={() => handleImageError(`menu-indicator-${index}`)}
											/>
										)}
									</div>
									<span className={`text-[#E67A2E] text-[15px] transition-all ${isActive ? 'font-semibold' : 'font-normal group-hover:font-medium'}`}>
										{item.id}
									</span>
								</button>
							);
						})}
					</div>
				</div>
			</div>
			
		</div>
	);
}

