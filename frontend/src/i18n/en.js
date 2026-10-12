// All English text. To add a sentence, add it here AND in hi.js, then use t('section.key').
const en = {
  nav: {
    monitor: 'Monitor',
    understand: 'Understand',
    reduce: 'Reduce',
    together: 'Together',
    language: 'Language',
  },

  hero: {
    line1: 'Smarter Campuses',
    line2Before: 'for a ',
    line2Accent: 'Greener Tomorrow',
    subtitle: 'Track resources. Take action. Create real impact.',
  },

  roles: {
    chooseRole: 'Choose your role',
    student: 'User',
    admin: 'Admin',
  },

  auth: {
    welcome: 'Welcome',
    studentSubtitle: 'Enter your mobile number to get a one-time code',
    adminSubtitle: 'Continue to your account',
    mobileNumber: 'Mobile number',
    sendOtp: 'Send OTP',
    sending: 'Sending',
    enterOtp: 'Enter the OTP',
    otpSentTo: 'We sent a 6-digit code to {phone}',
    otpLabel: '6-digit OTP',
    verifyContinue: 'Verify and continue',
    verifying: 'Verifying',
    changeNumber: 'Change number',
    resendOtp: 'Resend OTP',
    resendIn: 'Resend OTP in {seconds}s',
    demoOtp: 'Demo OTP: {otp}',
    email: 'Email',
    password: 'Password',
    showPassword: 'Show password',
    hidePassword: 'Hide password',
    signInAdmin: 'Continue as Admin',
    signingIn: 'Signing in',
    forgotPassword: 'Forgot password?',
    backToSignIn: 'Back to sign in',
    resetTitle: 'Reset your password',
    resetPhoneSubtitle: 'Enter the mobile number linked to your admin account',
    newPasswordTitle: 'Create a new password',
    newPasswordSubtitle: 'Use at least {min} characters',
    newPassword: 'New password',
    confirmPassword: 'Confirm new password',
    resetPassword: 'Reset password',
    saving: 'Saving',
    resetDoneTitle: 'Password updated',
    resetDoneText: 'You can now sign in with your new password.',
  },

  login: {
    demoNote: 'Demo mode. All figures on this page are simulated.',
    impactUnavailable: 'Impact figures are unavailable right now. You can still sign in.',
  },

  impact: {
    carbon: { label: 'Carbon Emissions Saved', caption: 'Equivalent to {value} trees planted' },
    electricity: { label: 'Electricity Saved', caption: 'Powering {value} classrooms for a day' },
    water: { label: 'Water Saved', caption: 'Enough for {value} people for a day' },
    waste: { label: 'Waste Diverted', caption: 'From ending up in landfills' },
    increase: 'increase',
    decrease: 'decrease',
  },

  units: {
    kg: 'kg',
    kwh: 'kWh',
    litres: 'Litres',
  },

  // Local checks (done in the browser)
  errors: {
    phoneInvalid: 'Enter a valid 10-digit mobile number.',
    otpFormat: 'Enter the 6-digit OTP.',
    loginMissing: 'Enter your email and password.',
    passwordShort: 'Password must be at least {min} characters.',
    passwordMismatch: 'The two passwords do not match.',

    // Codes sent by the backend. Keep these names in sync with backend/app/routes/auth.py
    GENERIC: 'Something went wrong. Please try again.',
    NETWORK: 'Cannot reach the server. Check that the backend is running.',
    INVALID_CREDENTIALS: 'Incorrect email or password.',
    INVALID_OTP: 'That OTP is incorrect. Check the code and try again.',
    OTP_EXPIRED: 'That OTP has expired. Request a new one.',
    TOO_MANY_ATTEMPTS: 'Too many attempts. Please wait a few minutes and try again.',
    WRONG_ROLE: 'This account belongs to a different role. Switch tabs and try again.',
    RESET_SESSION_EXPIRED: 'Your reset session expired. Start again from your mobile number.',
  },

  dashboard: {
    title: '{app} dashboard',
    signedInAs: 'Signed in as {name} ({role}).',
    placeholder: 'The real dashboard goes here.',
    logout: 'Log out',
  },
}

export default en
