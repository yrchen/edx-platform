;(function (define) {
    'use strict';

    define(['backbone',
            'underscore',
            'gettext',
            'text!support/templates/certificates.underscore'],
           function (Backbone, _, gettext, certificatesTemplate) {
               var view = Backbone.View.extend({
                   initialize: function() {
                      // TODO
                   },

                   render: function() {
                      // TODO
                      this.$el.html(_.template(certificatesTemplate));
                   },
               });

               return view;
           });
}).call(this, define || RequireJS.define);
