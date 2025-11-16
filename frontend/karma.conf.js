const { join } = require('path');

module.exports = function (config) {
  config.set({
    basePath: '',
    frameworks: ['jasmine', '@angular-devkit/build-angular'],
    plugins: [
      require('karma-jasmine'),
      require('karma-chrome-launcher'),
      require('karma-jasmine-html-reporter'),
      require('karma-coverage'),
      require('karma-junit-reporter'),
      require('@angular-devkit/build-angular/plugins/karma'),
    ],
    client: {
      clearContext: false, // deja visible el reporte de Jasmine en el navegador
    },
    jasmineHtmlReporter: {
      suppressAll: true,
    },
    coverageReporter: {
      dir: join(__dirname, './coverage'),
      reporters: [
        // Reporte para SonarCloud (lcov.info)
        { type: 'lcov', subdir: '.' },

        // Reporte para Azure DevOps (Code Coverage tab)
        { type: 'cobertura', subdir: '.', file: 'cobertura.xml' },
      ],
    },
    junitReporter: {
      outputDir: join(__dirname, './test-results'),
      outputFile: 'unit-tests.xml',
      useBrowserName: false,
    },
    reporters: ['progress', 'kjhtml', 'junit'],
    port: 9876,
    colors: true,
    logLevel: config.LOG_INFO,
    autoWatch: true,
    browsers: ['ChromeHeadless'],
    singleRun: false,
    restartOnFileChange: true,
  });
};
