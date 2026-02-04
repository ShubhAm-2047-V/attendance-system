import 'package:flutter/material.dart';
import 'screens/splash_screen.dart';

void main() {
  runApp(const RollUpApp());
}

class RollUpApp extends StatelessWidget {
  const RollUpApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ROLLUP',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.deepPurple,
      ),
      home: const SplashScreen(),
    );
  }
}
