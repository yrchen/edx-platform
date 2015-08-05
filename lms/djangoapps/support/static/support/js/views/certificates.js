;(function (define) {
    'use strict';

    define([
        'backbone',
        'underscore',
        'gettext',
        'support/js/collections/certificate',
        'text!support/templates/certificates.underscore',
        'text!support/templates/certificates_results.underscore'
    ], function (Backbone, _, gettext, CertCollection, certificatesTpl, resultsTpl) {
        var view = Backbone.View.extend({
            events: {
                "submit .certificates-form": "search"
            },

            initialize: function() {
                _.bindAll(this, "search", "updateCertificates", "handleError");
                this.certificates = new CertCollection({});
            },

            render: function() {
                this.$el.html(_.template(certificatesTpl));
            },

            renderResults: function() {
                var $resultsDiv = $(".certificates-results", this.$el);
                $resultsDiv.html(_.template(resultsTpl, {certificates: this.certificates}));
            },

            search: function(event) {
                // Prevent form submission, since we're handling it ourselves.
                event.preventDefault();

                // Fetch the certificate collection for the given user
                this.certificates.setUsername(this.getUsernameForSearch());
                this.certificates.fetch({
                    success: this.updateCertificates,
                    error: this.handleError
                });
            },

            updateCertificates: function() {
                this.renderResults();
            },

            handleError: function() {
                alert("Error!");
            },

            getUsernameForSearch: function() {
                return $('.certificates-form input[name="username"]').val();
            },
        });

        return view;
    });
}).call(this, define || RequireJS.define);
