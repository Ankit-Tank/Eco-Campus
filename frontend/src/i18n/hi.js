import appHi from './hi.app.js'

// हिंदी अनुवाद. Same keys as en.js. If a key is missing here, the English text is shown instead.
const hi = {
  ...appHi,
  nav: {
    monitor: 'निगरानी',
    understand: 'समझें',
    reduce: 'घटाएँ',
    together: 'साथ मिलकर',
    language: 'भाषा',
  },

  hero: {
    line1: 'स्मार्ट कैंपस',
    line2Before: '',
    line2Accent: 'हरित कल के लिए',
    subtitle: 'संसाधनों पर नज़र रखें। कदम उठाएँ। सच्चा बदलाव लाएँ।',
  },

  roles: {
    chooseRole: 'अपनी भूमिका चुनें',
    student: 'उपयोगकर्ता',
    admin: 'एडमिन',
  },

  auth: {
    welcome: 'स्वागत है',
    studentSubtitle: 'वन-टाइम कोड पाने के लिए अपना मोबाइल नंबर दर्ज करें',
    adminSubtitle: 'अपने खाते में आगे बढ़ें',
    mobileNumber: 'मोबाइल नंबर',
    sendOtp: 'OTP भेजें',
    sending: 'भेजा जा रहा है',
    enterOtp: 'OTP दर्ज करें',
    otpSentTo: 'हमने {phone} पर 6 अंकों का कोड भेजा है',
    otpLabel: '6 अंकों का OTP',
    verifyContinue: 'सत्यापित करें और आगे बढ़ें',
    verifying: 'सत्यापित हो रहा है',
    changeNumber: 'नंबर बदलें',
    resendOtp: 'OTP दोबारा भेजें',
    resendIn: '{seconds} सेकंड में OTP दोबारा भेजें',
    demoOtp: 'डेमो OTP: {otp}',
    email: 'ईमेल',
    password: 'पासवर्ड',
    showPassword: 'पासवर्ड दिखाएँ',
    hidePassword: 'पासवर्ड छिपाएँ',
    signInAdmin: 'एडमिन के रूप में आगे बढ़ें',
    signingIn: 'साइन इन हो रहा है',
    forgotPassword: 'पासवर्ड भूल गए?',
    backToSignIn: 'साइन इन पर वापस जाएँ',
    resetTitle: 'पासवर्ड रीसेट करें',
    resetPhoneSubtitle: 'अपने एडमिन खाते से जुड़ा मोबाइल नंबर दर्ज करें',
    newPasswordTitle: 'नया पासवर्ड बनाएँ',
    newPasswordSubtitle: 'कम से कम {min} अक्षर रखें',
    newPassword: 'नया पासवर्ड',
    confirmPassword: 'नया पासवर्ड दोबारा लिखें',
    resetPassword: 'पासवर्ड रीसेट करें',
    saving: 'सहेजा जा रहा है',
    resetDoneTitle: 'पासवर्ड बदल गया',
    resetDoneText: 'अब आप अपने नए पासवर्ड से साइन इन कर सकते हैं।',
  },

  login: {
    demoNote: 'डेमो मोड। इस पेज के सभी आँकड़े सिम्युलेटेड हैं।',
    impactUnavailable: 'आँकड़े अभी उपलब्ध नहीं हैं। आप फिर भी साइन इन कर सकते हैं।',
  },

  impact: {
    carbon: { label: 'बचाया गया कार्बन उत्सर्जन', caption: '{value} पेड़ लगाने के बराबर' },
    electricity: { label: 'बचाई गई बिजली', caption: '{value} कक्षाओं को एक दिन बिजली देने जितनी' },
    water: { label: 'बचाया गया पानी', caption: '{value} लोगों के एक दिन के लिए पर्याप्त' },
    waste: { label: 'लैंडफिल से बचा कचरा', caption: 'लैंडफिल में जाने से रोका गया' },
    increase: 'वृद्धि',
    decrease: 'कमी',
  },

  units: {
    kg: 'किग्रा',
    kwh: 'kWh',
    litres: 'लीटर',
  },

  errors: {
    phoneInvalid: 'सही 10 अंकों का मोबाइल नंबर दर्ज करें।',
    otpFormat: '6 अंकों का OTP दर्ज करें।',
    loginMissing: 'अपना ईमेल और पासवर्ड दर्ज करें।',
    passwordShort: 'पासवर्ड कम से कम {min} अक्षर का होना चाहिए।',
    passwordMismatch: 'दोनों पासवर्ड एक जैसे नहीं हैं।',

    GENERIC: 'कुछ गड़बड़ हो गई। कृपया फिर कोशिश करें।',
    NETWORK: 'सर्वर से संपर्क नहीं हो पा रहा। जाँचें कि बैकएंड चालू है।',
    INVALID_CREDENTIALS: 'ईमेल या पासवर्ड गलत है।',
    INVALID_OTP: 'यह OTP गलत है। कोड जाँचकर फिर कोशिश करें।',
    OTP_EXPIRED: 'इस OTP की समय-सीमा खत्म हो गई है। नया OTP माँगें।',
    TOO_MANY_ATTEMPTS: 'बहुत ज़्यादा कोशिशें हो गईं। कुछ मिनट रुककर फिर कोशिश करें।',
    WRONG_ROLE: 'यह खाता किसी दूसरी भूमिका का है। टैब बदलकर फिर कोशिश करें।',
    RESET_SESSION_EXPIRED: 'रीसेट का समय समाप्त हो गया। मोबाइल नंबर से दोबारा शुरू करें।',
  },

  dashboard: {
    title: '{app} डैशबोर्ड',
    signedInAs: '{name} ({role}) के रूप में साइन इन',
    placeholder: 'असली डैशबोर्ड यहाँ बनेगा।',
    logout: 'लॉग आउट',
  },
}

export default hi
