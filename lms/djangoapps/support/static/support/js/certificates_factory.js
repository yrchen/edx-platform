;(function (define) {
    'use strict';

    define(['jquery', 'support/js/views/certificates'],
        function ($, CertificatesView) {
            return function (options) {
                var view = new CertificatesView({
                    el: $('.certificates-content')
                });
                view.render();
            };
        });
}).call(this, define || RequireJS.define);
