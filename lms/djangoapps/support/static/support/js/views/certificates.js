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

            initialize: function(options) {
                _.bindAll(this, "search", "updateCertificates", "regenerateCertificate", "handleError");
                this.certificates = new CertCollection({});
                this.initialQuery = options.userQuery || null;
            },

            render: function() {
                this.$el.html(_.template(certificatesTpl));

                // TODO
                if (this.initialQuery) {
                    this.setUserQuery(this.initialQuery);
                    this.triggerSearch();
                }
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

                // Fetch the certificate collection for the given user
                var query = this.getUserQuery(),
                    url = "/support/certificates?query=" + query;

                // Prevent form submission, since we're handling it ourselves.
                event.preventDefault();

                // TODO -- explain
                window.history.pushState({}, window.document.title, url);

                // TODO
                this.certificates.setUserQuery(query);
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
                    success: function() {
                        this.certificates.fetch({
                            success: this.updateCertificates,
                            error: this.handleError,
                        });
                    },
                    error: this.handleError
                });
            },

            handleError: function() {
                this.renderError();
            },

            triggerSearch: function() {
                $('.certificates-form').submit();
            },

            getUserQuery: function() {
                return $('.certificates-form input[name="query"]').val();
            },

            setUserQuery: function(query) {
                $('.certificates-form input[name="query"]').val(query);
            },

            setResults: function(html) {
                var $resultsDiv = $(".certificates-results", this.$el);
                $resultsDiv.html(html);
            }
        });

        return view;
    });
}).call(this, define || RequireJS.define);
