;(function (define) {
    'use strict';

    define(['jquery', 'underscore', 'support/js/views/certificates'],
        function ($, _, CertificatesView) {
            return function (options) {
                var view = new CertificatesView(_.extend(options, {el: $('.certificates-content')}));
                view.render();
            };
        });
}).call(this, define || RequireJS.define);
