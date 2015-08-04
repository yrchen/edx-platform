;(function (define) {
    'use strict';

    define(['jquery', 'underscore', 'backbone', 'support/js/views/certificates'],
        function ($, _, Backbone, CertificatesView) {
            return function (options) {
                var view = new CertificatesView();
                view.render();
            };
        });
}).call(this, define || RequireJS.define);
