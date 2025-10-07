require 'etc'

require "jekyll"
require "jekyll-resize"

module JekylLResizeConcurrent
  class IngredientsGenerator < Jekyll::Generator
            
    safe true

    OPTIONS = [
      "800x>",
      "395x>",
      "100x>",
    ]
    NUM_THREADS = Etc.nprocessors * 2

    def generate(site)

      input_files = site.static_files.filter{|f| f.relative_path.start_with?("/assets") && f.relative_path.end_with?(".jpg")}.map{|f| f.relative_path}
      q = Queue.new

      threads = (0..NUM_THREADS).map{
        Thread.new{
          while i = q.deq
            f, o = i
            Jekyll::Resize.resize_impl(site, f, o)
          end
        }
      }

      for f in input_files do
        for o in OPTIONS do
          q << [f, o]
        end
      end
      q.close
      threads.each{|thread| thread.join}
    end
  end
end