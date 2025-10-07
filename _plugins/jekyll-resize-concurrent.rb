require 'etc'

require "jekyll"
require "jekyll-resize"

module JekylLResizeConcurrent
  class IngredientsGenerator < Jekyll::Generator
            
    safe true

    OPTIONS = [
      ["/assets/enhanced", "800x>"],
      ["/assets/enhanced", "100x>"],
      ["/assets/recipe_crops", "395x>"],
      ["/assets/recipe_crops", "100x>"],
      ["/assets/recipe_photos", "395x>"],
    ]
    NUM_THREADS = Etc.nprocessors * 2

    def generate(site)

      input_files = site.static_files.map{|f| f.relative_path}
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
        for prefix, option in OPTIONS do
          if f.start_with? prefix
            q << [f, option]
          end
        end
      end
      q.close
      threads.each{|thread| thread.join}
    end
  end
end