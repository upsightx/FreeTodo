import 'package:flutter/material.dart';

class AppModeProvider extends ChangeNotifier {
  bool _useMockData = true;

  bool get useMockData => _useMockData;

  void setUseMockData(bool value) {
    if (_useMockData == value) return;
    _useMockData = value;
    notifyListeners();
  }

  void toggle() {
    setUseMockData(!_useMockData);
  }
}
