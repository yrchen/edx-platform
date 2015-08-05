;(function (define) {
    'use strict';
    define(['backbone', 'support/js/models/certificate'],
        function(Backbone, CertModel) {
            var CertCollection = Backbone.Collection.extend({
                model: CertModel,

                initialize: function(options) {
                    this.userQuery = options.userQuery || "";
                },

                setUserQuery: function(userQuery) {
                    this.userQuery = userQuery;
                },

                url: function() {
                    return "/certificates/search?query=" + this.userQuery;
                }
            });
            return CertCollection;
    });
}).call(this, define || RequireJS.define);
