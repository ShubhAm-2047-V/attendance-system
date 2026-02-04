import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'teacher_dashboard.dart';

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF7F2FA),
      body: Center(
        child: ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.deepPurple,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(
              horizontal: 40,
              vertical: 16,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(30),
            ),
          ),
          onPressed: () async {
            final prefs = await SharedPreferences.getInstance();
            await prefs.setBool('isTeacherLoggedIn', true);

            if (!context.mounted) return;

            Navigator.pushReplacement(
              context,
              MaterialPageRoute(
                builder: (_) => const TeacherDashboard(),
              ),
            );
          },
          child: const Text(
            'Login as Teacher',
            style: TextStyle(fontSize: 16),
          ),
        ),
      ),
    );
  }
}
