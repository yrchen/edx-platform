;(function (define) {
    'use strict';

    define(['jquery', 'teams/js/views/teams_tab', 'teams/js/collections/topic'],
        function ($, TeamsTabView, TopicCollection) {
            return function (element, topics, topics_url, course_id) {
                var topicCollection = new TopicCollection(topics, {url: topics_url, course_id: course_id, parse: true});
                topicCollection.bootstrap();
                var view = new TeamsTabView({
                    el: element,
                    topicCollection: topicCollection
                });
                view.render();
                console.log("This is a new version!");
            };
        });
}).call(this, define || RequireJS.define);
