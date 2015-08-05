;(function (define) {
    'use strict';
    define(['backbone', 'support/js/models/certificate'],
        function(Backbone, CertModel) {
            var CertCollection = Backbone.Collection.extend({
                model: CertModel,

                initialize: function(options) {
                    this.username = options.username || "";
                },

                setUsername: function(username) {
                    this.username = username;
                },

                url: function() {
                    return "/certificates/user/" + this.username;
                }
            });
            return CertCollection;
    });
}).call(this, define || RequireJS.define);
