import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'core/app_store.dart';
import 'core/push_notifications.dart';
import 'ui/screens.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await PushNotifications.initialize();
  final store = AppStore();
  await store.restore();
  runApp(AgroEscudoApp(store: store));
}

class AgroEscudoApp extends StatelessWidget {
  AgroEscudoApp({super.key, required this.store})
    : router = GoRouter(
        refreshListenable: store,
        initialLocation: '/app',
        redirect: (_, state) {
          final loggingIn = state.matchedLocation == '/login';
          if (!store.authenticated) return loggingIn ? null : '/login';
          return loggingIn ? '/app' : null;
        },
        routes: [
          GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
          GoRoute(path: '/app', builder: (_, _) => const MobileShell()),
        ],
      );

  final AppStore store;
  final GoRouter router;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: store,
      child: MaterialApp.router(
        title: 'AgroEscudo',
        debugShowCheckedModeBanner: false,
        routerConfig: router,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xff047857),
            primary: const Color(0xff075b44),
            secondary: const Color(0xffc89116),
            surface: Colors.white,
          ),
          scaffoldBackgroundColor: const Color(0xfff5f8f6),
          fontFamily: 'Roboto',
          appBarTheme: const AppBarTheme(
            backgroundColor: Color(0xff053f31),
            foregroundColor: Colors.white,
            elevation: 0,
          ),
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: Colors.white,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: Color(0xffd9e5df)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: Color(0xffd9e5df)),
            ),
          ),
          cardTheme: CardThemeData(
            color: Colors.white,
            elevation: 0,
            margin: EdgeInsets.zero,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: const BorderSide(color: Color(0xffdfe9e4)),
            ),
          ),
          elevatedButtonTheme: ElevatedButtonThemeData(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xff075b44),
              foregroundColor: Colors.white,
              minimumSize: const Size.fromHeight(48),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
          ),
          useMaterial3: true,
        ),
      ),
    );
  }
}
