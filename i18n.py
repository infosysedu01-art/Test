# -*- coding: utf-8 -*-
"""Hindi translations. English text is the key; add a new pair here to translate new UI text."""

MONTHS_HI = ['जनवरी', 'फ़रवरी', 'मार्च', 'अप्रैल', 'मई', 'जून',
             'जुलाई', 'अगस्त', 'सितंबर', 'अक्टूबर', 'नवंबर', 'दिसंबर']

# strings the attendance-sheet JavaScript needs
JS_KEYS = [
    'Click: mark everyone Present for this day', 'Days', 'Code', 'Employee', 'Present per day',
    'No active employees found for this ward / work type / shift. Add them in Employees first.',
    'This cell cannot be edited (future date / past limit / permission).',
    'You do not have delete permission.', 'Copied',
    'Marked {n} employee(s) Present.', 'Marked {n} day(s) Present (Sundays skipped).',
    'Marked {n} Sunday(s) as Weekly Off.', 'No changes to save.', 'Could not save', 'Saved',
    'Skipped (permission / date)', 'Could not connect to the server', 'Unsaved changes',
    "Father's Name", 'Designation', 'View Employee',
    'Showing {n} of {m} employees', 'No employee matches your search.', 'search results only', 'Saving...',
]

HI = {
    # general
    'Ward Wise Attendance Management System': 'वार्ड वार उपस्थिति प्रबंधन प्रणाली',
    'Dashboard': 'डैशबोर्ड', 'Attendance': 'उपस्थिति', 'Attendance Sheet': 'उपस्थिति शीट',
    'Reports': 'रिपोर्ट', 'Masters': 'मास्टर', 'Employees': 'कर्मचारी', 'Employee': 'कर्मचारी',
    'Zone': 'ज़ोन', 'Ward': 'वार्ड', 'Wards': 'वार्ड', 'wards': 'वार्ड',
    'Administration': 'प्रशासन', 'Users & Access': 'यूज़र एवं एक्सेस',
    'Logout': 'लॉग आउट', 'Login': 'लॉगिन', 'Super Admin': 'सुपर एडमिन', 'User': 'यूज़र',
    'Save': 'सेव करें', 'Cancel': 'रद्द करें', 'Edit': 'संपादित करें', 'Delete': 'हटाएँ',
    'Update': 'अपडेट करें', 'Action': 'कार्रवाई', 'Search': 'खोजें', 'Show': 'दिखाएँ',
    'Print': 'प्रिंट करें', 'All': 'सभी', 'None': 'कोई नहीं', 'Active': 'सक्रिय',
    'Inactive': 'निष्क्रिय', 'Disabled': 'अक्षम', 'Name': 'नाम', 'Code': 'कोड',
    'Mobile': 'मोबाइल', 'Status': 'स्थिति', 'Date': 'दिनांक', 'From': 'से', 'To': 'तक',
    'Month': 'माह', 'Total': 'कुल', 'Days': 'दिन', 'days': 'दिन', 'Total Days': 'कुल दिन',
    'S.No': 'क्र.सं.', 'Remark': 'टिप्पणी', 'Location': 'स्थान', 'In Time': 'आने का समय',
    'No records found.': 'कोई रिकॉर्ड नहीं मिला।',
    'No records found for this filter.': 'इस फ़िल्टर के लिए कोई रिकॉर्ड नहीं मिला।',
    'No employees found.': 'कोई कर्मचारी नहीं मिला।',
    # statuses / shifts / work
    'Present': 'उपस्थित', 'Absent': 'अनुपस्थित', 'Leave': 'अवकाश', 'Half Day': 'अर्ध दिवस',
    'Weekly Off': 'साप्ताहिक अवकाश', 'Day': 'दिन', 'Night': 'रात', 'Shift': 'शिफ़्ट',
    'Shifts': 'शिफ़्ट', 'Work Type': 'कार्य का प्रकार', 'Work Types': 'कार्य के प्रकार',
    'Door to Door': 'डोर टू डोर', 'Commercial': 'कमर्शियल', 'Sweeping': 'स्वीपिंग',
    # login
    'Welcome back': 'वापसी पर स्वागत है', 'Sign in to your account to continue': 'आगे बढ़ने के लिए अपने खाते में लॉगिन करें',
    'Username': 'यूज़रनेम', 'Password': 'पासवर्ड', 'Enter your username': 'अपना यूज़रनेम लिखें',
    'Enter your password': 'अपना पासवर्ड लिखें', 'Show / hide password': 'पासवर्ड दिखाएँ / छुपाएँ',
    'Caps Lock is on': 'Caps Lock चालू है', 'Keep me signed in': 'मुझे लॉगिन रखें',
    'Forgot password? Contact your administrator.': 'पासवर्ड भूल गए? अपने एडमिनिस्ट्रेटर से संपर्क करें।',
    'Signing in...': 'लॉगिन हो रहा है...',
    'Authorised users only. All activity is recorded.': 'केवल अधिकृत यूज़र के लिए। सभी गतिविधियाँ दर्ज की जाती हैं।',
    'All rights reserved': 'सर्वाधिकार सुरक्षित',
    'Excel-style monthly attendance sheet': 'एक्सेल जैसी मासिक उपस्थिति शीट',
    'Day / Night shifts with Door to Door, Commercial and Sweeping tracking': 'दिन / रात की शिफ़्ट के साथ डोर टू डोर, कमर्शियल और स्वीपिंग की निगरानी',
    'Zone and ward wise employee management': 'ज़ोन और वार्ड के अनुसार कर्मचारी प्रबंधन',
    'Role based access and downloadable reports': 'भूमिका आधारित एक्सेस और डाउनलोड योग्य रिपोर्ट',
    'Incorrect username or password.': 'यूज़रनेम या पासवर्ड गलत है।',
    'Too many failed attempts. Please try again after 5 minutes.': 'बहुत अधिक गलत प्रयास हुए। कृपया 5 मिनट बाद पुनः प्रयास करें।',
    'This account is disabled. Please contact the administrator.': 'यह खाता बंद है। कृपया एडमिनिस्ट्रेटर से संपर्क करें।',
    # dashboard
    'Active Employees': 'सक्रिय कर्मचारी', 'Your Wards': 'आपके वार्ड', "Today's Attendance": 'आज की उपस्थिति',
    'Leave / Half Day': 'अवकाश / अर्ध दिवस', 'Day Shift Present': 'दिन की शिफ़्ट में उपस्थित',
    'Night Shift Present': 'रात की शिफ़्ट में उपस्थित', 'Who is working on what today': 'आज कौन कौन सा कार्य कर रहा है',
    # zone / ward
    'Zone Master': 'ज़ोन मास्टर', 'Zone Name': 'ज़ोन का नाम', 'Add Zone': 'ज़ोन जोड़ें',
    'Ward Master': 'वार्ड मास्टर', 'Ward Name / No.': 'वार्ड का नाम / नंबर', 'Add Ward': 'वार्ड जोड़ें',
    '-- Select Zone --': '-- ज़ोन चुनें --', '-- Select Ward --': '-- वार्ड चुनें --',
    'Delete this zone?': 'क्या यह ज़ोन हटाना है?', 'Delete this ward?': 'क्या यह वार्ड हटाना है?',
    'Delete this user?': 'क्या यह यूज़र हटाना है?',
    'Zone updated.': 'ज़ोन अपडेट हो गया।', 'Zone added.': 'ज़ोन जोड़ दिया गया।', 'Zone deleted.': 'ज़ोन हटा दिया गया।',
    'Please enter the zone name.': 'कृपया ज़ोन का नाम लिखें।', 'This zone already exists.': 'यह ज़ोन पहले से मौजूद है।',
    'This zone has wards. Delete the wards first.': 'इस ज़ोन में वार्ड हैं। पहले वार्ड हटाएँ।',
    'Zone and ward name are required.': 'ज़ोन और वार्ड का नाम आवश्यक है।',
    'Ward updated.': 'वार्ड अपडेट हो गया।', 'Ward added.': 'वार्ड जोड़ दिया गया।', 'Ward deleted.': 'वार्ड हटा दिया गया।',
    'This ward has employees. Remove or move them first.': 'इस वार्ड में कर्मचारी हैं। पहले उन्हें हटाएँ या दूसरे वार्ड में भेजें।',
    # employees
    'Add Employee': 'कर्मचारी जोड़ें', 'Edit Employee': 'कर्मचारी संपादित करें', 'Name / Code / Mobile': 'नाम / कोड / मोबाइल',
    'Designation': 'पद', 'Employee Code (auto)': 'कर्मचारी कोड (स्वतः)', "Father's Name": 'पिता का नाम',
    'Default Shift': 'सामान्य शिफ़्ट', 'Default Work': 'सामान्य कार्य', 'Joining Date': 'नियुक्ति तिथि',
    "This will also delete the employee's attendance records. Continue?": 'इससे कर्मचारी की उपस्थिति का रिकॉर्ड भी हट जाएगा। जारी रखें?',
    'Employee added. Code:': 'कर्मचारी जोड़ दिया गया। कोड:', 'Employee updated.': 'कर्मचारी अपडेट हो गया।',
    'Employee deleted.': 'कर्मचारी हटा दिया गया।',
    'You do not have access to add employees in this ward or work type.': 'आपको इस वार्ड या कार्य प्रकार में कर्मचारी जोड़ने का अधिकार नहीं है।',
    'You do not have access to keep an employee in this ward or work type.': 'आपको इस वार्ड या कार्य प्रकार में कर्मचारी रखने का अधिकार नहीं है।',
    # attendance sheet
    'Open Sheet': 'शीट खोलें', 'Previous Month': 'पिछला माह', 'Next Month': 'अगला माह',
    'Download Excel': 'एक्सेल डाउनलोड करें', 'Mark Sundays as Weekly Off': 'रविवार को साप्ताहिक अवकाश करें',
    'Keys': 'कुंजियाँ', 'Selected': 'चयनित', 'Location / Place of work': 'स्थान / कार्य स्थल',
    'Mark this employee Present for the month': 'इस कर्मचारी को पूरे माह उपस्थित करें',
    'Select Month, Ward, Shift and Work Type above, then click Open Sheet.': 'ऊपर माह, वार्ड, शिफ़्ट और कार्य का प्रकार चुनें, फिर "शीट खोलें" दबाएँ।',
    'Select a cell and type P / A / L / H / W. Delete clears it, arrow keys move, Ctrl+C / Ctrl+V copies and pastes. Click a day number to mark everyone Present for that day.':
        'सेल चुनकर P / A / L / H / W टाइप करें। Delete से साफ़ होगा, ऐरो कीज़ से आगे-पीछे जाएँ, Ctrl+C / Ctrl+V से कॉपी-पेस्ट करें। किसी तारीख़ पर क्लिक करने से उस दिन सभी उपस्थित हो जाएँगे।',
    'No ward / work type / shift has been assigned to you. Please contact the Super Admin.':
        'आपको कोई वार्ड / कार्य प्रकार / शिफ़्ट नहीं दी गई है। कृपया सुपर एडमिन से संपर्क करें।',
    'Click: mark everyone Present for this day': 'क्लिक करें: इस दिन सभी को उपस्थित करें',
    'Present per day': 'प्रतिदिन उपस्थित',
    'No active employees found for this ward / work type / shift. Add them in Employees first.':
        'इस वार्ड / कार्य प्रकार / शिफ़्ट में कोई सक्रिय कर्मचारी नहीं है। पहले "कर्मचारी" में जोड़ें।',
    'This cell cannot be edited (future date / past limit / permission).': 'यह सेल संपादित नहीं हो सकता (आगे की तारीख़ / पुरानी तारीख़ की सीमा / अनुमति)।',
    'You do not have delete permission.': 'आपको हटाने की अनुमति नहीं है।', 'Copied': 'कॉपी हो गया',
    'Marked {n} employee(s) Present.': '{n} कर्मचारी को उपस्थित किया गया।',
    'Marked {n} day(s) Present (Sundays skipped).': '{n} दिन उपस्थित किए गए (रविवार छोड़कर)।',
    'Marked {n} Sunday(s) as Weekly Off.': '{n} रविवार साप्ताहिक अवकाश किए गए।',
    'No changes to save.': 'सेव करने के लिए कोई बदलाव नहीं है।', 'Could not save': 'सेव नहीं हो सका',
    'Saved': 'सेव हो गया', 'Skipped (permission / date)': 'छोड़े गए (अनुमति / तारीख़)',
    'Could not connect to the server': 'सर्वर से कनेक्ट नहीं हो सका', 'Unsaved changes': 'बदलाव सेव नहीं हुए',
    'Attendance Register': 'उपस्थिति रजिस्टर', 'Attendance Report': 'उपस्थिति रिपोर्ट',
    'Invalid data': 'गलत डेटा', 'You do not have access to this ward / shift / work type': 'आपको इस वार्ड / शिफ़्ट / कार्य प्रकार का अधिकार नहीं है',
    'Emp Code': 'कर्मचारी कोड',
    # users
    'Create User': 'यूज़र बनाएँ', 'Edit User': 'यूज़र संपादित करें', 'Role': 'भूमिका', 'Full Name': 'पूरा नाम',
    'Back-date Limit': 'पिछली तारीख़ की सीमा', 'Back-date edit limit': 'पिछली तारीख़ में बदलाव की सीमा',
    'Unlimited': 'असीमित', 'Edit / Access': 'संपादित करें / एक्सेस', 'Module': 'मॉड्यूल',
    'leave blank to keep the same': 'वही रखने के लिए खाली छोड़ें', 'blank = no limit': 'खाली = कोई सीमा नहीं',
    'Super Admin has full access to everything. For a normal user, choose the access below.':
        'सुपर एडमिन के पास सभी चीज़ों का पूरा एक्सेस होता है। सामान्य यूज़र के लिए नीचे एक्सेस चुनें।',
    'Page / Action Access': 'पेज / कार्य का एक्सेस', 'Quick Preset': 'त्वरित सेटिंग',
    'Full Access': 'पूरा एक्सेस', 'Attendance Entry Only': 'केवल उपस्थिति भरना', 'View + Download Only': 'केवल देखना + डाउनलोड',
    'Clear All': 'सब हटाएँ', 'Attendance Sheet ': 'उपस्थिति शीट',
    'View': 'देखें', 'Add': 'जोड़ें', 'Export': 'एक्सपोर्ट', 'Export / Download': 'एक्सपोर्ट / डाउनलोड',
    'Data Access (what the user can work on)': 'डेटा एक्सेस (यूज़र किस पर कार्य कर सकता है)',
    'Work Type (Door to Door / Sweeping / Commercial)': 'कार्य का प्रकार (डोर टू डोर / स्वीपिंग / कमर्शियल)',
    'Allow all': 'सभी की अनुमति', 'Add wards in the Ward master first.': 'पहले वार्ड मास्टर में वार्ड जोड़ें।',
    'For example, 2 means the user can change attendance of today and the previous 2 days only. Nobody can mark future dates.':
        'उदाहरण: 2 का मतलब है कि यूज़र केवल आज और पिछले 2 दिन की उपस्थिति बदल सकता है। आगे की तारीख़ कोई नहीं भर सकता।',
    'This username already exists.': 'यह यूज़रनेम पहले से मौजूद है।',
    'Password must be at least 6 characters.': 'पासवर्ड कम से कम 6 अक्षर का होना चाहिए।',
    'User created.': 'यूज़र बना दिया गया।', 'User updated.': 'यूज़र अपडेट हो गया।', 'User deleted.': 'यूज़र हटा दिया गया।',
    'You cannot delete your own account.': 'आप अपना खुद का खाता नहीं हटा सकते।',
    'You do not have access to this page.': 'आपको इस पेज का एक्सेस नहीं है।',
    # reports
    'Attendance Report ': 'उपस्थिति रिपोर्ट',
}
HI['Attendance Sheet '] = HI['Attendance Sheet']

HI.update({
    'Change Password': 'पासवर्ड बदलें', 'Current Password': 'वर्तमान पासवर्ड', 'New Password': 'नया पासवर्ड',
    'Confirm New Password': 'नया पासवर्ड दोबारा लिखें', 'Update Password': 'पासवर्ड अपडेट करें',
    'Use at least 6 characters.': 'कम से कम 6 अक्षर रखें।',
    'Current password is incorrect.': 'वर्तमान पासवर्ड गलत है।',
    'New password and confirmation do not match.': 'नया पासवर्ड और पुष्टि पासवर्ड मेल नहीं खाते।',
    'New password must be different from the current password.': 'नया पासवर्ड वर्तमान पासवर्ड से अलग होना चाहिए।',
    'Password changed successfully.': 'पासवर्ड सफलतापूर्वक बदल गया।',
    'You must change your password before continuing.': 'आगे बढ़ने से पहले आपको अपना पासवर्ड बदलना होगा।',
    'Reset Password': 'पासवर्ड रीसेट करें', 'Reset password for': 'इस यूज़र का पासवर्ड रीसेट करें',
    'Generate Password': 'पासवर्ड बनाएँ',
    'Ask the user to change the password at next login': 'यूज़र से अगले लॉगिन पर पासवर्ड बदलवाएँ',
    'Password reset successfully for user:': 'पासवर्ड सफलतापूर्वक रीसेट हुआ, यूज़र:',
    'Employee Details': 'कर्मचारी विवरण', 'View Employee': 'कर्मचारी देखें', 'Back to Employees': 'कर्मचारियों की सूची पर वापस',
    'Employee Code': 'कर्मचारी कोड', 'Days Worked': 'काम किए गए दिन', 'Employee Attendance': 'कर्मचारी उपस्थिति',
    'No attendance records for this month.': 'इस माह का कोई उपस्थिति रिकॉर्ड नहीं है।',
})

HI.update({
    'Ward Reports': 'वार्ड रिपोर्ट', 'Report Type': 'रिपोर्ट का प्रकार', 'Daily': 'दैनिक', 'Weekly': 'साप्ताहिक', 'Monthly': 'मासिक',
    'All Wards': 'सभी वार्ड', 'All Shifts': 'सभी शिफ़्ट', 'All Work Types': 'सभी कार्य प्रकार',
    'Show Report': 'रिपोर्ट दिखाएँ', 'Print Report': 'रिपोर्ट प्रिंट करें', 'Any date of the week': 'सप्ताह की कोई भी तारीख़',
    'Choose the report type, ward and period above, then click Show Report.': 'ऊपर रिपोर्ट का प्रकार, वार्ड और अवधि चुनें, फिर "रिपोर्ट दिखाएँ" दबाएँ।',
    'No ward found for this selection.': 'इस चयन के लिए कोई वार्ड नहीं मिला।',
    'No employees found for this ward.': 'इस वार्ड में कोई कर्मचारी नहीं मिला।',
    'Daily Attendance Report': 'दैनिक उपस्थिति रिपोर्ट', 'Weekly Attendance Report': 'साप्ताहिक उपस्थिति रिपोर्ट',
    'Monthly Attendance Report': 'मासिक उपस्थिति रिपोर्ट', 'Period': 'अवधि', 'Generated on': 'तैयार किया गया',
    'Not Marked': 'अंकित नहीं', 'Total Employees': 'कुल कर्मचारी', 'Prepared By': 'तैयारकर्ता',
    'Verified By': 'सत्यापनकर्ता', 'Authorised Signatory': 'अधिकृत हस्ताक्षरकर्ता',
})

HI.update({
    'Holiday': 'सार्वजनिक छुट्टी', 'Holidays': 'छुट्टियाँ', 'Holiday Master': 'छुट्टी मास्टर', 'Holiday Name': 'छुट्टी का नाम',
    'Add Holiday': 'छुट्टी जोड़ें', 'Year': 'वर्ष', 'Sunday': 'रविवार', 'Sundays': 'रविवार', 'Working Days': 'कुल कार्य दिवस',
    'Calendar View': 'कैलेंडर व्यू', 'Details': 'विवरण', 'Day Type': 'दिन का प्रकार',
    'Click a date to see its details.': 'किसी तारीख़ पर क्लिक करके उसका विवरण देखें।',
    'Holiday added.': 'छुट्टी जोड़ दी गई।', 'Holiday updated.': 'छुट्टी अपडेट हो गई।', 'Holiday deleted.': 'छुट्टी हटा दी गई।',
    'Please enter the holiday date and name.': 'कृपया छुट्टी की तारीख़ और नाम लिखें।',
    'A holiday already exists on this date.': 'इस तारीख़ पर पहले से छुट्टी दर्ज है।',
    'Delete this holiday?': 'क्या यह छुट्टी हटानी है?',
    'Sundays are highlighted automatically. Add other holidays here so they are highlighted in the calendar and attendance sheet.':
        'रविवार अपने आप हाइलाइट होते हैं। अन्य छुट्टियाँ यहाँ जोड़ें ताकि वे कैलेंडर और उपस्थिति शीट में हाइलाइट हों।',
})

HI.update({'Welcome': 'स्वागत है'})

HI.update({'Please confirm': 'कृपया पुष्टि करें', 'Yes, continue': 'हाँ, जारी रखें'})

HI.update({
    'Zone Access (the user will see only these zones and their wards)': 'ज़ोन एक्सेस (यूज़र केवल इन्हीं ज़ोन और उनके वार्ड देख पाएगा)',
    'Ward (narrows the access further inside the allowed zones)': 'वार्ड (अनुमत ज़ोन के अंदर एक्सेस और सीमित करता है)',
    'Add zones in the Zone master first.': 'पहले ज़ोन मास्टर में ज़ोन जोड़ें।',
    'You cannot add a zone because your access is limited to specific zones.': 'आपका एक्सेस कुछ चुने हुए ज़ोन तक सीमित है, इसलिए आप नया ज़ोन नहीं जोड़ सकते।',
})

HI.update({'Overview': 'सारांश', 'Last 7 Days (Present)': 'पिछले 7 दिन (उपस्थित)', 'Upcoming Holidays': 'आने वाली छुट्टियाँ',
           'No upcoming holidays.': 'कोई आने वाली छुट्टी नहीं है।'})

HI.update({
    'Search employee by name, code, father name or designation...': 'नाम, कोड, पिता का नाम या पद से कर्मचारी खोजें...',
    'Showing {n} of {m} employees': '{m} में से {n} कर्मचारी दिख रहे हैं',
    'No employee matches your search.': 'आपकी खोज से कोई कर्मचारी नहीं मिला।',
    'search results only': 'केवल खोज परिणाम', 'Press / to search': '/ दबाकर खोजें', 'Clear': 'साफ़ करें',
})

HI.update({'Rows per page': 'प्रति पेज पंक्तियाँ', 'Showing {a} to {b} of {n} employees': '{n} कर्मचारियों में से {a} से {b} तक दिख रहे हैं',
           'First': 'पहला', 'Last': 'अंतिम', 'Previous': 'पिछला', 'Next': 'अगला'})

HI.update({
    'Password must be at least 8 characters and contain letters and numbers.': 'पासवर्ड कम से कम 8 अक्षर का हो और उसमें अक्षर व अंक दोनों हों।',
    'Your session expired or the form was invalid. Please refresh the page and try again.': 'आपका सेशन समाप्त हो गया या फ़ॉर्म अमान्य था। कृपया पेज रीफ़्रेश करके दोबारा प्रयास करें।',
    'Too many changes in one save. Please save in smaller parts.': 'एक बार में बहुत अधिक बदलाव हैं। कृपया छोटे हिस्सों में सेव करें।',
    'Someone else saved at the same time. Please reload the sheet and try again.': 'किसी और ने उसी समय सेव किया है। कृपया शीट रीलोड करके दोबारा प्रयास करें।',
    'Only the first 60 wards are shown. Choose a single ward or zone to see the rest.': 'केवल पहले 60 वार्ड दिखाए गए हैं। बाकी देखने के लिए एक वार्ड या ज़ोन चुनें।',
    'Showing {a} to {b} of {n} records': '{n} रिकॉर्ड में से {a} से {b} तक दिख रहे हैं',
    'Audit Log': 'ऑडिट लॉग', 'Action': 'कार्रवाई', 'Back': 'वापस',
    'Access denied': 'प्रवेश वर्जित', 'You do not have permission to open this page.': 'आपको यह पेज खोलने की अनुमति नहीं है।',
    'Page not found': 'पेज नहीं मिला', 'The page you are looking for does not exist.': 'आप जो पेज खोज रहे हैं वह मौजूद नहीं है।',
    'Not allowed': 'अनुमति नहीं', 'This action is not allowed.': 'यह कार्रवाई अनुमत नहीं है।',
    'Too much data': 'डेटा बहुत अधिक है', 'The request was too large.': 'अनुरोध बहुत बड़ा था।',
    'Too many requests': 'बहुत अधिक अनुरोध', 'Please wait a moment and try again.': 'कृपया थोड़ा रुककर दोबारा प्रयास करें।',
    'Server is busy': 'सर्वर व्यस्त है', 'The database is busy right now. Please try again in a few seconds.': 'डेटाबेस अभी व्यस्त है। कृपया कुछ सेकंड बाद दोबारा प्रयास करें।',
    'Something went wrong': 'कुछ गड़बड़ हो गई', 'The error has been recorded. Please try again; if it continues, contact the administrator.': 'त्रुटि दर्ज कर ली गई है। कृपया दोबारा प्रयास करें; समस्या बनी रहे तो एडमिनिस्ट्रेटर से संपर्क करें।',
})

HI.update({'Loading...': 'लोड हो रहा है...', 'Saving...': 'सेव हो रहा है...', 'Deleting...': 'हटाया जा रहा है...',
           'Preparing your download...': 'आपकी डाउनलोड फ़ाइल तैयार हो रही है...'})

HI.update({
    # vehicles
    'Vehicle': 'वाहन', 'Vehicles': 'वाहन', 'Vehicle Master': 'वाहन मास्टर', 'Vehicle Number': 'वाहन नंबर', 'Vehicle Type': 'वाहन का प्रकार',
    'Add Vehicle': 'वाहन जोड़ें', 'Edit Vehicle': 'वाहन संपादित करें', 'Back to Vehicles': 'वाहनों की सूची पर वापस',
    'Vehicle added.': 'वाहन जोड़ दिया गया।', 'Vehicle updated.': 'वाहन अपडेट हो गया।', 'Vehicle deleted.': 'वाहन हटा दिया गया।',
    'Delete this vehicle?': 'क्या यह वाहन हटाना है?', 'No vehicles found.': 'कोई वाहन नहीं मिला।',
    'Showing {a} to {b} of {n} vehicles': '{n} वाहनों में से {a} से {b} तक दिख रहे हैं',
    'Vehicle number, type or driver / helper name': 'वाहन नंबर, प्रकार या ड्राइवर / हेल्पर का नाम',
    'Letters, numbers, space or hyphen.': 'अक्षर, अंक, स्पेस या हाइफ़न।',
    'Enter a valid vehicle number (letters, numbers, space or hyphen, 3 to 20 characters).': 'सही वाहन नंबर लिखें (अक्षर, अंक, स्पेस या हाइफ़न; 3 से 20 अक्षर)।',
    'This vehicle number already exists.': 'यह वाहन नंबर पहले से मौजूद है।',
    'Please select a zone.': 'कृपया ज़ोन चुनें।',
    'The selected ward does not belong to the selected zone.': 'चुना हुआ वार्ड चुने हुए ज़ोन का नहीं है।',
    'Some crew members belong to another zone. Remove them from the vehicle before changing its zone.': 'कुछ क्रू सदस्य दूसरे ज़ोन के हैं। ज़ोन बदलने से पहले उन्हें वाहन से हटाएँ।',
    'This vehicle still has crew assigned. Open the vehicle and remove them first.': 'इस वाहन पर अभी क्रू जुड़ा है। पहले वाहन खोलकर उन्हें हटाएँ।',
    'Please choose a valid vehicle.': 'कृपया सही वाहन चुनें।',
    'The selected vehicle does not belong to the selected zone.': 'चुना हुआ वाहन चुने हुए ज़ोन का नहीं है।',
    'This vehicle is inactive. Choose an active vehicle.': 'यह वाहन निष्क्रिय है। सक्रिय वाहन चुनें।',
    '-- All wards of the zone --': '-- ज़ोन के सभी वार्ड --', 'All wards of the zone': 'ज़ोन के सभी वार्ड',
    '-- No vehicle --': '-- कोई वाहन नहीं --', '-- Select Designation --': '-- पद चुनें --', '-- Select employee --': '-- कर्मचारी चुनें --',
    'Only for Driver and Helper.': 'केवल ड्राइवर और हेल्पर के लिए।',
    # crew
    'Driver': 'ड्राइवर', 'Helper': 'हेल्पर', 'Others': 'अन्य', 'No driver': 'ड्राइवर नहीं', 'No helper': 'हेल्पर नहीं',
    'Crew on this vehicle': 'इस वाहन पर क्रू', 'Nobody assigned yet.': 'अभी कोई नहीं जुड़ा।',
    'Remove': 'हटाएँ', 'Remove this employee from the vehicle?': 'क्या इस कर्मचारी को वाहन से हटाना है?',
    'Removed from the vehicle.': 'वाहन से हटा दिया गया।', 'Assign': 'जोड़ें', 'Assigned to the vehicle.': 'वाहन से जोड़ दिया गया।',
    'Assign a Driver / Helper to this vehicle': 'इस वाहन पर ड्राइवर / हेल्पर जोड़ें', 'now on': 'अभी इस पर',
    'Only active Drivers and Helpers of the same zone are listed. Choosing someone who is on another vehicle moves him here.': 'केवल उसी ज़ोन के सक्रिय ड्राइवर और हेल्पर दिखते हैं। जो दूसरे वाहन पर है उसे चुनने पर वह यहाँ आ जाएगा।',
    'This employee cannot be assigned to this vehicle.': 'इस कर्मचारी को इस वाहन से नहीं जोड़ा जा सकता।',
    # designations
    'Supervisor': 'सुपरवाइज़र', 'Sweeper': 'स्वीपर', 'Sanitation Worker': 'सफ़ाई कर्मचारी', 'Operator': 'ऑपरेटर', 'Clerk': 'क्लर्क',
    'Other': 'अन्य', 'Other Designation': 'अन्य पद',
    'Search employee by name, code, father name, designation or vehicle...': 'नाम, कोड, पिता का नाम, पद या वाहन नंबर से कर्मचारी खोजें...',
})
JS_KEYS_EXTRA = []

HI.update({
    'Back to Trackers': 'ट्रैकर सूची पर वापस', 'Trolleymen on this tracker': 'इस ट्रैकर पर ट्रॉलीमैन', 'Assign a Trolleyman to this tracker': 'इस ट्रैकर पर ट्रॉलीमैन जोड़ें',
    'Only active Trolleymen of the same zone are listed. Choosing someone who is on another tracker moves him here.': 'केवल इसी ज़ोन के सक्रिय ट्रॉलीमैन दिख रहे हैं। जो दूसरे ट्रैकर पर है उसे चुनने पर वह यहाँ आ जाएगा।',
    'Remove this employee from the tracker?': 'क्या इस कर्मचारी को ट्रैकर से हटाना है?', 'Assigned to the tracker.': 'ट्रैकर पर जोड़ दिया गया।', 'Removed from the tracker.': 'ट्रैकर से हटा दिया गया।',
    'This employee cannot be assigned to this tracker.': 'इस कर्मचारी को इस ट्रैकर पर नहीं जोड़ा जा सकता।',
    'Daily Attendance': 'दैनिक उपस्थिति', 'Open': 'खोलें', 'Select Date, Ward, Shift and Work Type above, then click Open.': 'ऊपर तारीख, वार्ड, शिफ्ट और कार्य प्रकार चुनकर खोलें दबाएँ।',
    'Mark all Present': 'सभी को उपस्थित करें', 'Present for not marked': 'जिनकी नहीं लगी उन्हें उपस्थित करें', 'Clear all': 'सब हटाएँ', 'Not marked': 'दर्ज नहीं',
    'Previous Day': 'पिछला दिन', 'Next Day': 'अगला दिन', 'This date cannot be edited.': 'इस तारीख में बदलाव नहीं हो सकता।', 'Attendance saved.': 'उपस्थिति सेव हो गई।', 'Skipped': 'छोड़े गए',
    'Clear every status on this page?': 'इस पेज की सभी उपस्थिति हटानी है?', 'No employees found.': 'कोई कर्मचारी नहीं मिला।',
    'Search by name, code, father name, mobile, vehicle, route or tracker': 'नाम, कोड, पिता का नाम, मोबाइल, वाहन, रूट या ट्रैकर से खोजें',
    'Tracker': 'ट्रैकर', 'Trackers': 'ट्रैकर', 'Tracker ID': 'ट्रैकर आईडी', 'Tracker Master': 'ट्रैकर मास्टर', 'Add Tracker': 'ट्रैकर जोड़ें', 'Edit Tracker': 'ट्रैकर बदलें',
    'Trolleyman': 'ट्रॉलीमैन', '-- No tracker --': '-- कोई ट्रैकर नहीं --', 'Only for Trolleyman.': 'केवल ट्रॉलीमैन के लिए।', 'Only for Driver, Helper and Trolleyman.': 'केवल ड्राइवर, हेल्पर और ट्रॉलीमैन के लिए।',
    'Tracker added.': 'ट्रैकर जोड़ दिया गया।', 'Tracker updated.': 'ट्रैकर बदल दिया गया।', 'Tracker deleted.': 'ट्रैकर हटा दिया गया।', 'Delete this tracker?': 'क्या यह ट्रैकर हटाना है?', 'No trackers found.': 'कोई ट्रैकर नहीं मिला।',
    'This tracker ID already exists.': 'यह ट्रैकर आईडी पहले से मौजूद है।', 'Please choose a valid tracker.': 'कृपया सही ट्रैकर चुनें।', 'Tracker ID or trolleyman name': 'ट्रैकर आईडी या ट्रॉलीमैन का नाम',
    'The selected tracker does not belong to the selected zone.': 'चुना गया ट्रैकर चुने गए ज़ोन का नहीं है।', 'This tracker is inactive. Choose an active tracker.': 'यह ट्रैकर निष्क्रिय है। सक्रिय ट्रैकर चुनें।',
    'This tracker is still assigned to employees. Change their Tracker ID first.': 'यह ट्रैकर अभी कर्मचारियों को दिया गया है। पहले उनका ट्रैकर आईडी बदलें।',
    'Enter a valid tracker ID (letters, numbers, space or hyphen, up to 30 characters).': 'सही ट्रैकर आईडी लिखें (अक्षर, अंक, स्पेस या हाइफ़न, अधिकतम 30)।',
    'Some trolleymen belong to another zone. Remove them from the tracker before changing its zone.': 'कुछ ट्रॉलीमैन दूसरे ज़ोन के हैं। ज़ोन बदलने से पहले उन्हें हटाएं।',
    'Route': 'रूट', 'Routes': 'रूट', 'Route ID': 'रूट आईडी', 'Route Master': 'रूट मास्टर', 'Route Name / Area': 'रूट का नाम / क्षेत्र',
    'Add Route': 'रूट जोड़ें', 'Edit Route': 'रूट संपादित करें', 'Back to Routes': 'रूट की सूची पर वापस',
    'Route added.': 'रूट जोड़ दिया गया।', 'Route updated.': 'रूट अपडेट हो गया।', 'Route deleted.': 'रूट हटा दिया गया।',
    'Delete this route?': 'क्या यह रूट हटाना है?', 'No routes found.': 'कोई रूट नहीं मिला।',
    'Showing {a} to {b} of {n} routes': '{n} रूट में से {a} से {b} तक दिख रहे हैं',
    'Route ID, name or driver / helper name': 'रूट आईडी, नाम या ड्राइवर / हेल्पर का नाम',
    'Letters, numbers, space, hyphen or slash.': 'अक्षर, अंक, स्पेस, हाइफ़न या स्लैश।',
    'Enter a valid Route ID (letters, numbers, space, hyphen or slash, up to 20 characters).': 'सही रूट आईडी लिखें (अक्षर, अंक, स्पेस, हाइफ़न या स्लैश; अधिकतम 20 अक्षर)।',
    'This Route ID already exists.': 'यह रूट आईडी पहले से मौजूद है।',
    'Please choose a valid route.': 'कृपया सही रूट चुनें।',
    'The selected route does not belong to the selected zone.': 'चुना हुआ रूट चुने हुए ज़ोन का नहीं है।',
    'This route is inactive. Choose an active route.': 'यह रूट निष्क्रिय है। सक्रिय रूट चुनें।',
    'Some crew members belong to another zone. Remove them from the route before changing its zone.': 'कुछ क्रू सदस्य दूसरे ज़ोन के हैं। ज़ोन बदलने से पहले उन्हें रूट से हटाएँ।',
    'This route still has crew assigned. Open the route and remove them first.': 'इस रूट पर अभी क्रू जुड़ा है। पहले रूट खोलकर उन्हें हटाएँ।',
    'Crew on this route': 'इस रूट पर क्रू', 'Remove this employee from the route?': 'क्या इस कर्मचारी को रूट से हटाना है?',
    'Removed from the route.': 'रूट से हटा दिया गया।', 'Assigned to the route.': 'रूट से जोड़ दिया गया।',
    'Assign a Driver / Helper to this route': 'इस रूट पर ड्राइवर / हेल्पर जोड़ें',
    'Only active Drivers and Helpers of the same zone are listed. Choosing someone who is on another route moves him here.': 'केवल उसी ज़ोन के सक्रिय ड्राइवर और हेल्पर दिखते हैं। जो दूसरे रूट पर है उसे चुनने पर वह यहाँ आ जाएगा।',
    'This employee cannot be assigned to this route.': 'इस कर्मचारी को इस रूट से नहीं जोड़ा जा सकता।',
    '-- No route --': '-- कोई रूट नहीं --',
    'Search employee by name, code, father name, designation, vehicle or route...': 'नाम, कोड, पिता का नाम, पद, वाहन या रूट से कर्मचारी खोजें...',
})

HI.update({
    'This ward already exists in this zone.': 'यह वार्ड इस ज़ोन में पहले से मौजूद है।',
    'Please enter the employee name.': 'कृपया कर्मचारी का नाम लिखें।',
    'Please select the zone and the ward.': 'कृपया ज़ोन और वार्ड चुनें।',
    'Please choose a valid shift.': 'कृपया सही शिफ्ट चुनें।',
    'Username and full name are required.': 'यूज़रनेम और पूरा नाम ज़रूरी हैं।',
})

HI.update({
    'Project': 'प्रोजेक्ट', 'Projects': 'प्रोजेक्ट्स', 'Project Master': 'प्रोजेक्ट मास्टर', 'Project Name': 'प्रोजेक्ट का नाम',
    'Project Access': 'प्रोजेक्ट एक्सेस', 'Switch project': 'प्रोजेक्ट बदलें', 'All Projects': 'सभी प्रोजेक्ट',
    'Add Project': 'प्रोजेक्ट जोड़ें', 'Company Name': 'कंपनी का नाम', 'Code Prefix': 'कोड प्रीफ़िक्स',
    'Employee Code Prefix': 'कर्मचारी कोड प्रीफ़िक्स', 'Next': 'आगे', 'Checking...': 'जाँच हो रही है...',
    'Please enter the project name.': 'कृपया प्रोजेक्ट का नाम लिखें।', 'This project already exists.': 'यह प्रोजेक्ट पहले से मौजूद है।',
    'Project updated.': 'प्रोजेक्ट अपडेट हो गया।', 'Project added.': 'प्रोजेक्ट जुड़ गया।', 'Project deleted.': 'प्रोजेक्ट हटा दिया गया।',
    'Delete this project?': 'क्या यह प्रोजेक्ट हटाना है?', 'At least one project must stay active.': 'कम से कम एक प्रोजेक्ट सक्रिय रहना चाहिए।',
    'The last project cannot be deleted.': 'आख़िरी प्रोजेक्ट नहीं हटाया जा सकता।',
    'Please select at least one project for this user.': 'कृपया इस यूज़र के लिए कम से कम एक प्रोजेक्ट चुनें।',
    'Username not found. Please check it or contact the administrator.': 'यूज़रनेम नहीं मिला। कृपया जाँचें या एडमिन से संपर्क करें।',
    'No project is assigned to this user. Please contact the administrator.': 'इस यूज़र को कोई प्रोजेक्ट नहीं दिया गया है। कृपया एडमिन से संपर्क करें।',
    'No project is assigned to your account. Please contact the administrator.': 'आपके अकाउंट में कोई प्रोजेक्ट नहीं है। कृपया एडमिन से संपर्क करें।',
    'You do not have access to this project. Please contact the administrator.': 'आपको इस प्रोजेक्ट का एक्सेस नहीं है। कृपया एडमिन से संपर्क करें।',
    'Could not check the username. Please try again.': 'यूज़रनेम की जाँच नहीं हो सकी। कृपया फिर कोशिश करें।',
})

HI.update({
    'Type digits to search...': 'खोजने के लिए अंक लिखें...',
    'No match found': 'कोई मिलान नहीं मिला',
    'Showing the first 30 - type more digits to narrow': 'पहले 30 दिखा रहे हैं - सीमित करने के लिए और अंक लिखें',
    'Clear': 'हटाएँ',
})
