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
    expect(find.text('CUENTAS DE PILOTO'), findsOneWidget);
  });
}
