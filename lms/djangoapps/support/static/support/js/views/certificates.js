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
                "submit .certificates-form": "search",
                "click .btn-cert-regenerate": "regenerateCertificate"
            },

            initialize: function() {
                _.bindAll(this, "search", "updateCertificates", "regenerateCertificate", "handleError");
                this.certificates = new CertCollection({});
            },

            render: function() {
                this.$el.html(_.template(certificatesTpl));
            },

            renderResults: function() {
                var context = {
                    certificates: this.certificates,
                };

                this.setResults(_.template(resultsTpl, context));
            },

            renderError: function() {
                this.setResults(gettext("An unexpected error occurred.  Please try again."));
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

            regenerateCertificate: function(event) {
                var $button = $(event.target);

                $.ajax({
                    url: "/certificates/regenerate",
                    type: "POST",
                    data: {
                        username: $button.data("username"),
                        course_key: $button.data("course-key"),
                    },
                    context: this,
                    success: this.updateCertificates,
                    error: this.handleError
                });
            },

            handleError: function() {
                this.renderError();
            },

            getUsernameForSearch: function() {
                return $('.certificates-form input[name="username"]').val();
            },

            setResults: function(html) {
                var $resultsDiv = $(".certificates-results", this.$el);
                $resultsDiv.html(html);
            }
        });

        return view;
    });
}).call(this, define || RequireJS.define);
