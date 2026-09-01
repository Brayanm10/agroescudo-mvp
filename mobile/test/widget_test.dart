import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/app_store.dart';
import 'package:mobile/ui/screens.dart';
import 'package:provider/provider.dart';

void main() {
  testWidgets('shows the AgroEscudo pilot login', (tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AppStore(),
        child: const MaterialApp(home: LoginScreen()),
      ),
    );

    expect(find.text('AgroEscudo'), findsOneWidget);
    expect(find.text('Acceso seguro'), findsOneWidget);
    expect(find.text('Ingresar'), findsOneWidget);
    expect(find.text('Crear cuenta para mi operacion'), findsOneWidget);
    expect(find.text('CUENTAS DE PILOTO'), findsNothing);
  });

  testWidgets('shows a simple client signup with optional Sentinel contact', (
    tester,
  ) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AppStore(),
        child: const MaterialApp(home: SignupScreen()),
      ),
    );

    expect(find.text('Tu operacion en AgroEscudo'), findsOneWidget);
    await tester.drag(find.byType(ListView), const Offset(0, -650));
    await tester.pumpAndSettle();
    expect(
      find.text('Contacto de urgencia Sentinel (opcional)'),
      findsOneWidget,
    );
    await tester.drag(find.byType(ListView), const Offset(0, -500));
    await tester.pumpAndSettle();
    expect(find.text('Solicitar mi cuenta'), findsOneWidget);
  });
}
