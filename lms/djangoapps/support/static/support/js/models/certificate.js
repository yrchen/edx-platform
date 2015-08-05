(function (define) {
    'use strict';
    define(['backbone'], function (Backbone) {
        var Certificate = Backbone.Model.extend({
            defaults: {
                course_key: null,
                type: null,
                status: null,
                download_url: null,
                grade: null,
                created: null,
                modified: null
            }
        });
        return Certificate;
    });
}).call(this, define || RequireJS.define);
